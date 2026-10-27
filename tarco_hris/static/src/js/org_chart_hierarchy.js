/** @odoo-module **/

import { hierarchyView } from "@web_hierarchy/hierarchy_view";
import { HierarchyModel } from "@web_hierarchy/hierarchy_model";
import { registry } from "@web/core/registry";
import { hrEmployeeHierarchyView } from "@hr_org_chart/views/hr_employee_hierarchy/hr_employee_hierarchy_view";

/**
 * Load the full forest at once and keep every branch open.
 * Standard Odoo hierarchy only shows roots and collapses the other
 * manager when you click "N people".
 */
export class TarcoHierarchyModel extends HierarchyModel {
    isSearchDefaultOrEmpty() {
        return false;
    }

    _searchNodeToCollapse() {
        return null;
    }
}

registry.category("views").add("tarco_full_hierarchy", {
    ...hierarchyView,
    Model: TarcoHierarchyModel,
});

registry.category("views").add("tarco_hr_employee_hierarchy", {
    ...hrEmployeeHierarchyView,
    Model: TarcoHierarchyModel,
});
