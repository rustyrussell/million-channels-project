from igraph import drawing

def igraphDraw(ig, bbox=(0,0,2000,2000)):
    """
    draw graph using igraph obj
    :param ig: igraph obj
    :return:
    """
    ig.vs["label"] = ig.vs.indices
    drawing.plot(ig, bbox=bbox)

