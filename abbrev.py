from bidict import bidict


ABBREV_MAP = bidict(
    aug="augmentations",
    reg="regularization",
    con="consistency",
    arch="architectures",
    act="activations",
    norm="normalizations",
    tr="transformers",
    cl="contrastive learning",
    kd="knowledge-distillation",
    wsl="weakly-supervised learning",
    ssl="semi-supervised learning",
    pseudo="pseudo-labeling",
    usl="unsupervised learning",
    tl="transfer learning",
    xsl="x-shot learning",
    fsl="few-shot learning",
    osl="one-shot learning",
    zsl="zero-shot learning",
    ft="fine-tuning",
    od="detection",
    det="detectors",
    sod="salient object detection",
    seg="segmentation",
    nas="neural architecture search",
    comp="compression",
    mob="mobile vision",
    gan="generative adversarial networks",
    adv="adversarial",    
    ae="autoencoders",
    vb="variational bayes",
    opt="optimization",
    hyp="hyperparameter",
    da="domain adaptation",
    rec="recognition",
    ner="perception and the visual cortex",
    de="differential evolution",
    llvp="low-level visual processing",
    stat="statistics"
)
"""
hcc = []
for index in range(max(hch) + 1):
    if index % 2000:
        print(f"[{index}/{max(hch) + 1}]")
    c = map(lambda x: x == index, hcc)
"""