import NodegraphAPI

__all__ = ['get_output_nodes']


def get_output_nodes(include_image_write_nodes):
    """
    get_output_nodes(include_image_write_nodes)

    Returns a list of nodes that are candidates for job submission. This will include all Render nodes
    and optionally ImageWrite nodes in the scene that are not bypassed.

    :param include_image_write_nodes: Whether to include ImageWrite nodes (True) in the results,
           or only Render nodes (False)
    :return: A list of the candidate output nodes.
    """

    # Always include Render nodes
    nodes = NodegraphAPI.GetAllNodesByType("Render")

    # Conditionally include ImageWrite nodes
    if include_image_write_nodes:
        nodes += NodegraphAPI.GetAllNodesByType("ImageWrite")

    # Ignore bypassed nodes
    nodes = [node for node in nodes if not node.isBypassed()]
    return nodes