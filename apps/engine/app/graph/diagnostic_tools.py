from __future__ import annotations

from typing import Any


def tool_call(tool_name: str, endpoint: str, tool_input: dict[str, Any] | None = None) -> dict[str, Any]:
    return {"tool_name": tool_name, "tool_endpoint": endpoint, "tool_input": tool_input or {}}


def govc_endpoint(tool_name: str, entity: str | None = None) -> dict[str, Any]:
    mapping = {
        "govc_about": ("/api/v1/govc/about", {}),
        "govc_vm_info": ("/api/v1/govc/vm-info", {"name": entity} if entity else {}),
        "govc_host_info": ("/api/v1/govc/host-info", {"name": entity} if entity else {}),
        "govc_datastore_info": ("/api/v1/govc/datastore-info", {}),
        "govc_events": ("/api/v1/govc/events", {}),
        "govc_volume_ls": ("/api/v1/govc/volume-ls", {}),
    }
    endpoint, tool_input = mapping[tool_name]
    return tool_call(tool_name, endpoint, tool_input)


def rest_endpoint(tool_name: str, value: str | None = None) -> dict[str, Any]:
    mapping = {
        "vsphere_rest_about": ("/api/v1/vsphere-rest/about", {}),
        "vsphere_rest_appliance_health": ("/api/v1/vsphere-rest/appliance/health", {}),
        "vsphere_rest_list_tag_categories": ("/api/v1/vsphere-rest/tag-categories", {}),
        "vsphere_rest_list_tags": ("/api/v1/vsphere-rest/tags", {}),
        "vsphere_rest_list_attached_tags": (
            "/api/v1/vsphere-rest/tags/attached",
            {"object_id": value} if value else {},
        ),
        "vsphere_rest_list_content_libraries": ("/api/v1/vsphere-rest/content-libraries", {}),
        "vsphere_rest_list_library_items": (
            f"/api/v1/vsphere-rest/content-libraries/{value}/items" if value else "",
            {},
        ),
        "vsphere_rest_list_recent_tasks": ("/api/v1/vsphere-rest/tasks/recent", {}),
    }
    endpoint, tool_input = mapping[tool_name]
    return tool_call(tool_name, endpoint, tool_input)


def compare_calls(object_type: str, entity: str | None) -> list[dict[str, Any]]:
    if object_type == "host" and entity:
        return [
            tool_call("get_host_details", "/api/v1/context/host-details", {"name": entity}),
            govc_endpoint("govc_host_info", entity),
        ]
    if object_type == "vm" and entity:
        return [
            tool_call("get_vm_details", "/api/v1/context/vm-details", {"name": entity}),
            govc_endpoint("govc_vm_info", entity),
        ]
    if object_type == "datastore":
        return [
            tool_call("list_datastores", "/api/v1/inventory/datastores"),
            govc_endpoint("govc_datastore_info"),
        ]
    return []
