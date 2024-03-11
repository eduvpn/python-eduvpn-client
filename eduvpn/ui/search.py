import enum
from typing import Dict, List

from gi.overrides.Gtk import ListStore  # type: ignore

from eduvpn.discovery import DiscoOrganization, DiscoServer
from eduvpn.i18n import retrieve_country_name
from eduvpn.server import InstituteServer, SecureInternetServer, Server
from eduvpn.ui.utils import show_ui_component
from eduvpn.utils import run_in_background_thread, run_in_glib_thread


class ServerGroup(enum.Enum):
    INSTITUTE_ACCESS = enum.auto()
    SECURE_INTERNET = enum.auto()
    OTHER = enum.auto()


group_scroll_component = {
    ServerGroup.INSTITUTE_ACCESS: "institute_list",
    ServerGroup.SECURE_INTERNET: "secure_internet_list",
    ServerGroup.OTHER: "other_server_list",
}

group_tree_component = {
    ServerGroup.INSTITUTE_ACCESS: "institute_list_tree",
    ServerGroup.SECURE_INTERNET: "secure_internet_list_tree",
    ServerGroup.OTHER: "other_server_list_tree",
}

group_header_component = {
    ServerGroup.INSTITUTE_ACCESS: "institute_list_header",
    ServerGroup.SECURE_INTERNET: "secure_internet_list_header",
    ServerGroup.OTHER: "other_server_list_header",
}


def new_group_model() -> ListStore:
    from gi.repository import GObject, Gtk

    return Gtk.ListStore(GObject.TYPE_STRING, GObject.TYPE_PYOBJECT)  # type: ignore


def server_to_model_data(server) -> list:
    display_string = str(server)
    if isinstance(server, SecureInternetServer):
        display_string = retrieve_country_name(server.country_code)
    return [display_string, server]


def show_result_components(window: "EduVpnGtkWindow", show: bool) -> None:  # type: ignore  # noqa: E0602
    """
    Set the visibility of essential server list related components.
    """
    window.show_page(window.find_server_page)
    window.current_shown_page = window.find_server_page
    show_ui_component(window.institute_list, show)
    show_ui_component(window.secure_internet_list, show)
    show_ui_component(window.other_server_list, show)


def show_search_components(window: "EduVpnGtkWindow", show: bool) -> None:  # type: ignore  # noqa: E0602
    """
    Set the visibility of essential search related components.
    """
    show_ui_component(window.find_server_search_form, show)
    show_ui_component(window.find_server_image, show)
    show_ui_component(window.find_server_label, show)
    show_ui_component(window.find_server_search_input, show)


def show_search_results(window: "EduVpnGtkWindow", show: bool) -> None:  # type: ignore  # noqa: E0602
    """
    Set the visibility of the tree of the search result component in the UI.
    """
    show_ui_component(window.server_list_container, show)


def group_servers(servers):
    """
    Separate the servers into three groups.
    """
    groups: Dict[ServerGroup, List[Server]] = {  # type: ignore
        ServerGroup.INSTITUTE_ACCESS: [],
        ServerGroup.SECURE_INTERNET: [],
        ServerGroup.OTHER: [],
    }
    for server in servers:
        if isinstance(server, InstituteServer) or (
            isinstance(server, DiscoServer) and server.server_type == "institute_access"
        ):
            groups[ServerGroup.INSTITUTE_ACCESS].append(server)
        elif isinstance(server, SecureInternetServer) or isinstance(
            server, DiscoOrganization
        ):
            groups[ServerGroup.SECURE_INTERNET].append(server)
        elif isinstance(server, Server):
            groups[ServerGroup.OTHER].append(server)
        else:
            continue
    return groups


def show_group_tree(window: "EduVpnGtkWindow", group: ServerGroup, show: bool) -> None:  # type: ignore  # noqa: E0602
    """
    Set the visibility of the tree of result for a server type.
    """
    # Hide secure internet list if a server is already available
    if group == ServerGroup.SECURE_INTERNET and window.can_disable_secure_internet:
        show = False

    scroll_component_name = group_scroll_component[group]
    scroll_component = getattr(window, scroll_component_name)
    show_ui_component(scroll_component, show)
    tree_component_name = group_tree_component[group]
    tree_component = getattr(window, tree_component_name)
    show_ui_component(tree_component, show)
    header_component_name = group_header_component[group]
    header_component = getattr(window, header_component_name)
    show_ui_component(header_component, show)


def init_server_search(window: "EduVpnGtkWindow") -> None:  # type: ignore  # noqa: E0602
    "Initialize the search page components."
    from gi.repository import Gtk, Pango

    text_cell = Gtk.CellRendererText()
    text_cell.props.ellipsize = Pango.EllipsizeMode.END  # type: ignore
    text_cell.set_property("size-points", 14)  # type: ignore
    text_cell.set_property("ypad", 10)  # type: ignore
    for group in group_tree_component:
        component_name = group_tree_component[group]
        tree_view = getattr(window, component_name)
        if len(tree_view.get_columns()) == 0:
            # Only add this column once.
            column = Gtk.TreeViewColumn("", text_cell, text=0)  # type: ignore
            tree_view.append_column(column)


@run_in_background_thread("search-exit")
def exit_server_search(window: "EduVpnGtkWindow") -> None:  # type: ignore  # noqa: E0602
    "Hide the search page components."
    for group in group_scroll_component:
        show_group_tree(window, group, False)
    show_search_results(window, False)


def update_search_results_for_type(
    window: "EduVpnGtkWindow", group: ServerGroup, servers  # type: ignore  # noqa: E0602
) -> None:
    """
    Update the UI with the search results
    for a single type of server.
    """
    from gi.repository import Gtk

    @run_in_background_thread("search-convert-model")
    def convert(servers, callback):
        model = new_group_model()  # type: ignore
        # Remove the old search results.
        for server in servers:
            model.append(server_to_model_data(server))

        sorted_model = Gtk.TreeModelSort(model=model)  # type: ignore
        sorted_model.set_sort_column_id(0, Gtk.SortType.ASCENDING)  # type: ignore
        callback(sorted_model)

    @run_in_glib_thread
    def callback(model):
        model_has_results = len(model) > 0  # type: ignore
        component_name = group_tree_component[group]
        tree_view = getattr(window, component_name)
        tree_view.set_model(model)
        show_group_tree(window, group, show=model_has_results)

    convert(servers, callback)


def update_results(window: "EduVpnGtkWindow", servers) -> None:  # type: ignore  # noqa: E0602
    """
    Update the UI with the search results.
    """
    if servers is None:
        show_search_results(window, False)
        return
    server_map = group_servers(servers)
    for group in group_scroll_component:
        update_search_results_for_type(
            window,
            group,
            server_map.get(group, []),
        )
    show_search_results(window, True)
