import os
import json
import argparse
import bibtexparser
from functools import partial
from ordered_set import OrderedSet
from collections import namedtuple



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
        return f"\\item {self.title} " + "\\cite{" + self.id + "}"

    def __repr__(self):
        return f"{self.title} [{self.id}]"

def parse_args():
    def path_fixer(p, suffix, must_exist):
        if not p.startswith("tex_stuff/"):
            assert p.count("/") == 0, p
            p = f"tex_stuff/{p}"
        
        if not p.endswith(suffix):
            p = f"{p}{suffix}"
        if must_exist:
            if not os.path.exists(p):
                raise TexRelatedFileNotFound(p)
        return p
 
    p = argparse.ArgumentParser()
    p.add_argument("-b", "--bibfiles", type=partial(path_fixer, suffix=".bib", must_exist=True), nargs="+", default=["bibliography"])
    p.add_argument("-f", "--fout", type=partial(path_fixer, suffix=".tex", must_exist=False), default="core")
    p.add_argument("-t", "--toc", type=partial(path_fixer, suffix=".json", must_exist=True), default="toc")
    return p.parse_args()


class IterBibTex:
    def __init__(self, bibpaths):
        self.bibpaths = tuple(bibpaths)

    def __iter__(self):
        for p in self.bibpaths:
            with open(p) as bibfile:
                bibs = bibtexparser.load(bibfile)
            for bt in bibs.entries:
                loc = tuple(bt.get("keywords", "no-category").split(","))
                yield CitedItem(
                    id=bt["ID"], location=loc, title=bt["title"])        

class CitationsMap:
    def __init__(self, allowed_keys):
        self.__d = dict()
        for k in allowed_keys:
            self.__d[k] = OrderedSet()

    def _check_key(self, k):
        if k not in self.__d:
            raise KeyError(f"input key '{k}' not one of:\n[{', '.join(list(self.__d))}]")

    def __add(self, __k, cited_item: CitedItem):
        self._check_key(__k)
        self.__d[__k].add(cited_item)

    def add(self, cited_item: CitedItem):
        for loc in cited_item.location:
            self.__add(loc, cited_item)

    def get(self, __k):
        self._check_key(__k)
        return tuple(self.__d[__k])

    def nested_sections(self):
        pm = dict()
        return pm

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

    def write_tex(d, depth=0):
        for k, v in d.items():
            tab = "\t" * k.count('::')
            if depth == 0:
                tex_body.append(tab + "\\addtocontents{toc}{\\setcounter{tocdepth}{3}}")
            tex_body.append(f"{tab}\\{k.count('::') * 'sub'}section" + "{" + k.split("::")[-1] + "}")
            tex_body.append(f"{tab}\\begin" + "{" + "enumerate" + "}")
            if isinstance(v, dict):
                write_tex(v, depth + 1)
            else:
                assert v is None, v
            for cited_item in cite_map.get(k):
                tex_body.append(tab + "\t" + cited_item.to_latex())
            tex_body.append(f"{tab}\\end" + "{" + "enumerate" + "}")
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
    bibtex_iter = IterBibTex(args.bibfiles)
    for citation in iter(bibtex_iter):
        cite_map.add(citation)
    tex_code = _TEX_IN.split("\n") + fill_tex_body(cite_map) + \
        ["\\newpage", "\\bibliographystyle{ACM-Reference-Format}"] + \
            ["\\bibliography{" + bibfile[bibfile.index("/") + 1: bibfile.index(".")] + "}" for bibfile in args.bibfiles] + \
                ["\\end{document}"]
    with open(args.fout, "w") as fout:
        fout.write("\n".join(tex_code))
    print(f"\nWritten to LaTeX file {args.fout}\n")



if __name__ == "__main__":
    main()




