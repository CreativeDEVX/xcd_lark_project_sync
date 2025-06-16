/** @odoo-module **/

// Import components using the full module path
import { many2oneAutocomplete } from "@xcd_lark_project_sync/js/many2one_autocomplete";
import { systrayItem } from "@xcd_lark_project_sync/js/xcd_lark_project_sync";

// Export the components
export { many2oneAutocomplete, systrayItem };

// Default export for backward compatibility
export default {
    many2oneAutocomplete,
    systrayItem
};
