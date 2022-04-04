import os
import json
import argparse
import bibtexparser
from bidict import bidict
from functools import partial
from ordered_set import OrderedSet
from collections import namedtuple

from abbrev import ABBREV_MAP


_TEX_IN = """\\documentclass[acmlarge]{acmart}
\\AtBeginDocument{%
\\providecommand\\BibTeX{{%
\\normalfont B\\kern-0.5em{\\scshape i\\kern-0.25em b}\\kern-0.8em\\TeX}}}
\\usepackage{setspace}
\\author{Luke Ottey} 
\\begin{document}
\\begin{center}
\\textbf{Deep Learning and Computer Vision Papers}
\\end{center}
Luke Ottey
\\newline
\\href{mailto:lottey98@gmail.com}{\\nolinkurl{lottey98@gmail.com}} 
\\singlespacing
\\tableofcontents
\\newpage"""



class TexRelatedFileNotFound(Exception):
    ...


class CitedItem(namedtuple("CitedItem", "id title location")):
    def to_latex(self):
        return f"\\item {self.title} " + "\\cite{" + self.id + "} "

    def __repr__(self):
        return f"{self.title} [{self.id}]"

def parse_args():
    def path_fixer(p, suffix, must_exist):
        if not p.startswith("tex_stuff/"):
            p = f"tex_stuff/{p}"
        assert p.count("/") == 1, p
        
        if not p.endswith(suffix):
            p = f"{p}{suffix}"
        if must_exist:
            if not os.path.exists(p):
                raise TexRelatedFileNotFound(p)
        return p
 
    p = argparse.ArgumentParser()
    p.add_argument("-b", "--bibfile", type=partial(path_fixer, suffix=".bib", must_exist=True), default="bibliography")
    p.add_argument("-f", "--fout", type=partial(path_fixer, suffix=".tex", must_exist=False), default="core")
    p.add_argument("-t", "--toc", type=partial(path_fixer, suffix=".json", must_exist=True), default="toc")
    p.add_argument("-k", "--key", type=str, default="none")
    return p.parse_args()


class IterBibTex:
    def __init__(self, bibpath, allowed_keys):
        self.bibpath = bibpath
        self.allowed_keys = allowed_keys

    def __iter__(self):
        with open(self.bibpath) as bibfile:
            bibs = bibtexparser.load(bibfile)
        for bt in bibs.entries:
            locs = list(map(lambda loc: "::".join([ABBREV_MAP.get(_k, _k) for _k in loc.split("::")]), bt.get("keywords", "no-category").split(","))) 
            for loc in locs:
                assert any(key.startswith(loc) for key in self.allowed_keys), loc
            yield CitedItem(
                id=bt["ID"], location=tuple(locs), title=bt["title"]) 


class CitationsMap:
    def __init__(self, allowed_keys):
        self.__d = dict()
        for k in allowed_keys:
            self.__d[k] = OrderedSet()

    def _check_key(self, k):
        k = "::".join([ABBREV_MAP.get(_k, _k) for _k in k.split("::")])  
        if k in self.__d:
            return k
        if not any(key.startswith(k) for key in list(self.__d)):
            raise KeyError(f"input key '{k}' not one of:\n[{', '.join(list(self.__d))}]")
        return k
    

    def __add(self, __k, cited_item: CitedItem):
        __k = self._check_key(__k)
        self.__d[__k].add(cited_item)

    def add(self, cited_item: CitedItem):
        for loc in cited_item.location:
            self.__add(loc, cited_item)

    def get(self, __k, mlvl=False, skip_check=False):
        if not skip_check:
            __k = self._check_key(__k)
        if not mlvl:
            return tuple(self.__d[__k])
        v = OrderedSet()
        for ___k in filter(lambda x: x.startswith(__k), self.toc()):
            for item in self.__d[___k]:
                v.add(item)
        return tuple(v)

    def toc(self):
        return tuple(self.__d)

    @classmethod
    def from_json(cls, path):
        with open(path, "r") as toc:
            cats_json = json.load(toc)
        nested_cats = []
        def inner(d, prefix_cat=None):
            if prefix_cat is None:
                prefix_cat = tuple()
            else:
                nested_cats.append("::".join(prefix_cat))
            for k, v in d.items():
                if isinstance(v, list):
                    nested_cats.append("::".join(prefix_cat + (k,)))
                else:
                    inner(v, prefix_cat + (k,))
        inner(cats_json)
        return cls(nested_cats)

    def __iter__(self):
        for k in self.toc():
            yield k

    def __repr__(self):
        return repr(self.__d)

def filter_wonocat(citations):
    return tuple(filter(lambda item: item.location != ("no-category",), citations))

def fill_tex_body(cite_map):

    mlvl_keys = dict()

    def make_sections(key):
        sub_keys = {}
        for k in list(filter(lambda k: k.startswith(key) and k != key, iter(cite_map))):
            sub_keys[k] = make_sections(k)
        if len(sub_keys) == 0:
            sub_keys = None
        return sub_keys

    for key in filter(lambda k: k.count("::") == 0, iter(cite_map)):
        mlvl_keys[key] = make_sections(key)
    tex_body = []
    used_keys = set()
    section_per_depth = ("section", "subsection", "subsubsection", "paragraph", "subparagraph")
    def write_tex(d, depth=0):
        for k, v in d.items():
            if k in used_keys:
                continue
            tab = "\t" * k.count('::')
            if depth == 0:
                tex_body.append(tab + "\\addtocontents{toc}{\\setcounter{tocdepth}{6}}")
            header = f"{tab}\\{section_per_depth[depth]}" + "{" + k.split("::")[-1] + "}"
            tex_body.append(header)
            cited_items = tuple(cite_map.get(k, mlvl=False, skip_check=True))
            
            if isinstance(v, dict):
                write_tex(v, depth + 1)
            else:
                assert v is None, v
            begin_enum = f"{tab}\\begin" + "{" + "enumerate" + "}"
            tex_body.append(begin_enum)
            for cited_item in cited_items:
                tex_body.append(tab + "\t" + cited_item.to_latex() + "\n")
            if tex_body[-1] == begin_enum and tex_body[-2] == header:
                tex_body.append(tab + "\t" + "\\item")
            
            tex_body.append(f"{tab}\\end" + "{" + "enumerate" + "}")

            used_keys.add(k)
    write_tex(mlvl_keys)
    return list(tex_body)


def main():
    args = parse_args()

    for path in ( 
        'tex_stuff/acmart.cls', 'tex_stuff/ACM-Reference-Format.bbx',
        'tex_stuff/ACM-Reference-Format.cbx', 'tex_stuff/ACM-Reference-Format.bst', 
        'tex_stuff/ACM-Reference-Format.dbx'):
        if not os.path.exists(path):
            raise TexRelatedFileNotFound(path)

    cite_map = CitationsMap.from_json(args.toc)
    bibtex_iter = IterBibTex(args.bibfile, tuple(cite_map.toc()))
    for citation in iter(bibtex_iter):
        cite_map.add(citation)
    
    if args.key != "none":
        print(f"------ {args.key.upper()} -------\n")
        for item in filter_wonocat(cite_map.get(cite_map._check_key(args.key), mlvl=True)):
            print([" | ".join(item.location)])
            print(item.to_latex(), "\n")
    else:
        tex_code = _TEX_IN.split("\n") + fill_tex_body(cite_map) + \
            ["\\newpage", "\\bibliographystyle{ACM-Reference-Format}"] + \
                ["\\bibliography{" + args.bibfile[args.bibfile.index("/") + 1: args.bibfile.index(".")] + "}", "\\end{document}"]

        with open(args.fout, "w") as fout:
            fout.write("\n".join(tex_code))
        print(f"\nWritten to LaTeX file {args.fout}\n")



if __name__ == "__main__":
    main()




