from typing import Optional, List, Dict, Iterable, Callable
from functools import lru_cache
from gi.repository import Gtk, GObject
from eduvpn.server import (
    ServerType, Server, InstituteAccessServer, OrganisationServer,
    CustomServer, ServerDatabase, group_servers_by_type)
from .utils import show_ui_component


location_type_tree_component = {
    InstituteAccessServer: 'instituteTreeView',
    OrganisationServer: 'secureInternetTreeView',
    CustomServer: 'otherServersTreeView',
}

location_type_header_component = {
    InstituteAccessServer: 'instituteAccessHeader',
    OrganisationServer: 'secureInternetHeader',
    CustomServer: 'otherServersHeader',
}

gtk_search_components = [
    # These are the components that need
    # to be shown on all search pages.
    'findYourInstitutePage',
    'instituteTreeView',
    'secureInternetTreeView',
    'otherServersTreeView',
    'findYourInstituteSpacer',
    'findYourInstituteImage',
    'findYourInstituteLabel',
    'findYourInstituteSearch',
]


Model = Gtk.ListStore


@lru_cache()
def get_server_type_model(server_type: ServerType) -> Model:
    # Model: (name: str, server: ServerType)
    return Gtk.ListStore(  # type: ignore
        GObject.TYPE_STRING,
        GObject.TYPE_PYOBJECT)


def server_to_model_data(server: Server) -> list:
    return [str(server), server]


def show_search_components(builder, show: bool):
    """
    Set the visibility of essential search related components.
    """
    for name in gtk_search_components:
        show_ui_component(builder, name, show)


def show_search_resuls(builder, show: bool):
    """
    Set the visibility of the tree of the search result component in the UI.
    """
    show_ui_component(builder, 'findYourInstituteScrolledWindow', show)


def show_server_type_tree(builder, server_type: ServerType, show: bool):
    """
    Set the visibility of the tree of result for a server type.
    """
    tree_component_name = location_type_tree_component[server_type]
    show_ui_component(builder, tree_component_name, show)
    header_component_name = location_type_header_component[server_type]
    show_ui_component(builder, header_component_name, show)


def init_server_search(builder):
    "Initialize the search page components."
    show_search_components(builder, True)
    text_cell = Gtk.CellRendererText()
    text_cell.set_property("size-points", 14)
    for server_type in location_type_tree_component:
        component_name = location_type_tree_component[server_type]
        tree_view = builder.get_object(component_name)
        column = Gtk.TreeViewColumn(None, text_cell, text=0)
        if len(tree_view.get_columns()) == 0:
            # Only add this column once.
            tree_view.append_column(column)
        model = get_server_type_model(server_type)
        tree_view.set_model(model)


def exit_server_search(builder):
    "Hide the search page components."
    show_search_components(builder, False)
    for server_type in location_type_tree_component:
        show_server_type_tree(builder, server_type, False)
    show_search_resuls(builder, False)


def connect_selection_handlers(builder, select_callback: Callable):
    "Connect the selection callback handlers for each server type."
    for server_type in location_type_tree_component:
        component_name = location_type_tree_component[server_type]
        tree_view = builder.get_object(component_name)
        selection = tree_view.get_selection()
        selection.connect("changed", select_callback)


def disconnect_selection_handlers(builder, select_callback: Callable):
    "Disconnect the selection callback handlers for each server type."
    for server_type in location_type_tree_component:
        component_name = location_type_tree_component[server_type]
        tree_view = builder.get_object(component_name)
        selection = tree_view.get_selection()
        selection.disconnect_by_func(select_callback)


def update_search_results_for_type(builder,
                                   server_type: ServerType,
                                   servers: Iterable[Server]):
    """
    Update the UI with the search results
    for a single type of server.
    """
    model = get_server_type_model(server_type)  # type: ignore
    # Remove the old search results.
    model.clear()  # type: ignore
    # Add the new search results.
    for server in servers:
        model_data = server_to_model_data(server)
        model.append(model_data)  # type: ignore
    # Update the UI.
    model_has_results = len(model) > 0  # type: ignore
    show_server_type_tree(builder, server_type, show=model_has_results)


def update_results(builder, servers: Optional[Iterable[Server]]):
    """
    Update the UI with the search results.
    """
    if servers is None:
        show_search_resuls(builder, False)
        return
    server_map = group_servers_by_type(servers)
    for server_type in location_type_tree_component:
        update_search_results_for_type(
            builder,
            server_type,
            server_map.get(server_type, []),
        )
    show_search_resuls(builder, True)
