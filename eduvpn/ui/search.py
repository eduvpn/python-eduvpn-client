from typing import Optional, Iterable, Callable, List, Dict
import enum
from functools import lru_cache
from gi.repository import Gtk, GObject, Pango
from eduvpn.server import (
    AnyServer as Server, InstituteAccessServer,
    OrganisationServer, SecureInternetLocation, CustomServer)
from .utils import show_ui_component


class ServerGroup(enum.Enum):
    INSTITUTE_ACCESS = enum.auto()
    SECURE_INTERNET = enum.auto()
    OTHER = enum.auto()


group_tree_component = {
    ServerGroup.INSTITUTE_ACCESS: 'institute_list',
    ServerGroup.SECURE_INTERNET: 'secure_internet_list',
    ServerGroup.OTHER: 'other_server_list',
}

group_header_component = {
    ServerGroup.INSTITUTE_ACCESS: 'institute_list_header',
    ServerGroup.SECURE_INTERNET: 'secure_internet_list_header',
    ServerGroup.OTHER: 'other_server_list_header',
}


# typing aliases
Model = Gtk.ListStore


@lru_cache()
def get_group_model(group: ServerGroup) -> Model:
    # Model: (name: str, server: ServerType)
    return Gtk.ListStore(  # type: ignore
        GObject.TYPE_STRING,
        GObject.TYPE_PYOBJECT)


def server_to_model_data(server: Server) -> list:
    return [str(server), server]


def show_result_components(window, show: bool):
    """
    Set the visibility of essential server list related components.
    """
    window.show_page(window.find_server_page)
    show_ui_component(window.institute_list, show)
    show_ui_component(window.secure_internet_list, show)
    show_ui_component(window.other_server_list, show)


def show_search_components(window, show: bool):
    """
    Set the visibility of essential search related components.
    """
    show_ui_component(window.find_server_search_form, show)
    show_ui_component(window.find_server_image, show)
    show_ui_component(window.find_server_label, show)
    show_ui_component(window.find_server_search_input, show)


def show_search_results(window, show: bool):
    """
    Set the visibility of the tree of the search result component in the UI.
    """
    show_ui_component(window.server_list_container, show)


def group_servers(
        servers: Iterable[Server]) -> Dict[ServerGroup, List[Server]]:
    """
    Separate the servers into three groups.
    """
    groups: Dict[ServerGroup, List[Server]] = {
        ServerGroup.INSTITUTE_ACCESS: [],
        ServerGroup.SECURE_INTERNET: [],
        ServerGroup.OTHER: [],
    }
    for server in servers:
        if isinstance(server, InstituteAccessServer):
            groups[ServerGroup.INSTITUTE_ACCESS].append(server)
        elif isinstance(server, (OrganisationServer, SecureInternetLocation)):
            groups[ServerGroup.SECURE_INTERNET].append(server)
        elif isinstance(server, CustomServer):
            groups[ServerGroup.OTHER].append(server)
        else:
            raise TypeError(server)
    return groups


def show_group_tree(window, group: ServerGroup, show: bool):
    """
    Set the visibility of the tree of result for a server type.
    """
    tree_component_name = group_tree_component[group]
    tree_component = getattr(window, tree_component_name)
    show_ui_component(tree_component, show)
    header_component_name = group_header_component[group]
    header_component = getattr(window, header_component_name)
    show_ui_component(header_component, show)


def init_server_search(window):
    "Initialize the search page components."
    text_cell = Gtk.CellRendererText()
    text_cell.props.ellipsize = Pango.EllipsizeMode.END
    text_cell.set_property("size-points", 14)
    for group in group_tree_component:
        component_name = group_tree_component[group]
        tree_view = getattr(window, component_name)
        if len(tree_view.get_columns()) == 0:
            # Only add this column once.
            column = Gtk.TreeViewColumn(None, text_cell, text=0)
            tree_view.append_column(column)
        model = get_group_model(group)
        tree_view.set_model(model)


def exit_server_search(window):
    "Hide the search page components."
    for group in group_tree_component:
        show_group_tree(window, group, False)
    show_search_results(window, False)


def connect_selection_handlers(window, select_callback: Callable):
    "Connect the selection callback handlers for each server type."
    for group in group_tree_component:
        component_name = group_tree_component[group]
        tree_view = getattr(window, component_name)
        selection = tree_view.get_selection()
        selection.connect("changed", select_callback)


def disconnect_selection_handlers(window, select_callback: Callable):
    "Disconnect the selection callback handlers for each server type."
    for group in group_tree_component:
        component_name = group_tree_component[group]
        tree_view = getattr(window, component_name)
        selection = tree_view.get_selection()
        selection.disconnect_by_func(select_callback)


def update_search_results_for_type(window,
                                   group: ServerGroup,
                                   servers: Iterable[Server]):
    """
    Update the UI with the search results
    for a single type of server.
    """
    model = get_group_model(group)  # type: ignore
    # Remove the old search results.
    model.clear()  # type: ignore
    # Add the new search results.
    for server in servers:
        model_data = server_to_model_data(server)
        model.append(model_data)  # type: ignore
    # Update the UI.
    model_has_results = len(model) > 0  # type: ignore
    show_group_tree(window, group, show=model_has_results)


def update_results(window, servers: Optional[Iterable[Server]]):
    """
    Update the UI with the search results.
    """
    if servers is None:
        show_search_results(window, False)
        return
    server_map = group_servers(servers)
    for group in group_tree_component:
        update_search_results_for_type(
            window,
            group,
            server_map.get(group, []),
        )
    show_search_results(window, True)
