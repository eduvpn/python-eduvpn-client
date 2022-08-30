import enum
from functools import lru_cache
from typing import Union, Dict, Iterable, List, Optional

from eduvpn.server import AnyServer as Server
from eduvpn.server import (CustomServer, InstituteAccessServer,
                           OrganisationServer)

from eduvpn.ui.utils import show_ui_component
from gi.overrides.Gtk import ListStore


class ServerGroup(enum.Enum):
    INSTITUTE_ACCESS = enum.auto()
    SECURE_INTERNET = enum.auto()
    OTHER = enum.auto()


group_tree_component = {
    ServerGroup.INSTITUTE_ACCESS: "institute_list",
    ServerGroup.SECURE_INTERNET: "secure_internet_list",
    ServerGroup.OTHER: "other_server_list",
}

group_header_component = {
    ServerGroup.INSTITUTE_ACCESS: "institute_list_header",
    ServerGroup.SECURE_INTERNET: "secure_internet_list_header",
    ServerGroup.OTHER: "other_server_list_header",
}


@lru_cache()
def get_group_model(group: ServerGroup) -> ListStore:
    # Model: (name: str, server: ServerType)
    from gi.repository import GObject, Gtk
    return Gtk.ListStore(GObject.TYPE_STRING, GObject.TYPE_PYOBJECT)  # type: ignore


def server_to_model_data(server: Server) -> list:
    return [str(server), server]


def show_result_components(window: 'EduVpnGtkWindow', show: bool) -> None:  # type: ignore
    """
    Set the visibility of essential server list related components.
    """
    window.show_page(window.find_server_page)
    show_ui_component(window.institute_list, show)
    show_ui_component(window.secure_internet_list, show)
    show_ui_component(window.other_server_list, show)


def show_search_components(window: 'EduVpnGtkWindow', show: bool) -> None:  # type: ignore
    """
    Set the visibility of essential search related components.
    """
    show_ui_component(window.find_server_search_form, show)
    show_ui_component(window.find_server_image, show)
    show_ui_component(window.find_server_label, show)
    show_ui_component(window.find_server_search_input, show)


def show_search_results(window: 'EduVpnGtkWindow', show: bool) -> None:  # type: ignore
    """
    Set the visibility of the tree of the search result component in the UI.
    """
    show_ui_component(window.server_list_container, show)


def group_servers(servers: Iterable[Server]) -> Dict[ServerGroup, List[Server]]:
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
        elif isinstance(server, OrganisationServer):
            groups[ServerGroup.SECURE_INTERNET].append(server)
        elif isinstance(server, CustomServer):
            groups[ServerGroup.OTHER].append(server)
        else:
            raise TypeError(server)
    return groups


def show_group_tree(window: 'EduVpnGtkWindow', group: ServerGroup, show: bool) -> None:  # type: ignore
    """
    Set the visibility of the tree of result for a server type.
    """
    tree_component_name = group_tree_component[group]
    tree_component = getattr(window, tree_component_name)
    show_ui_component(tree_component, show)
    header_component_name = group_header_component[group]
    header_component = getattr(window, header_component_name)
    show_ui_component(header_component, show)


def init_server_search(window: 'EduVpnGtkWindow') -> None:  # type: ignore
    "Initialize the search page components."
    from gi.repository import Gtk, Pango
    text_cell = Gtk.CellRendererText()
    text_cell.props.ellipsize = Pango.EllipsizeMode.END
    text_cell.set_property("size-points", 14)
    for group in group_tree_component:
        component_name = group_tree_component[group]
        tree_view = getattr(window, component_name)
        if len(tree_view.get_columns()) == 0:
            # Only add this column once.
            column = Gtk.TreeViewColumn("", text_cell, text=0)
            tree_view.append_column(column)
        model = get_group_model(group)
        tree_view.set_model(model)


def exit_server_search(window: 'EduVpnGtkWindow') -> None:  # type: ignore
    "Hide the search page components."
    for group in group_tree_component:
        show_group_tree(window, group, False)
    show_search_results(window, False)


def update_search_results_for_type(
    window: 'EduVpnGtkWindow', group: ServerGroup, servers: Iterable[Server]  # type: ignore
) -> None:
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

def update_results(window: 'EduVpnGtkWindow', servers: Optional[Iterable[Server]]) -> None:  # type: ignore
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
