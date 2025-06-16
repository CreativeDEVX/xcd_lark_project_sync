/** @odoo-module */

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";
import { Component, onWillStart, useRef, onMounted, onError } from "@odoo/owl";
import { browser } from "@web/core/browser/browser";

/**
 * Custom Many2OneAutocomplete widget for Lark Tasklist selection
 * Enhances the standard many2one with autocomplete and custom filtering
 */
class Many2OneAutocomplete extends Component {
    setup() {
        super.setup();
        this.orm = useService("orm");
        this.notification = useService("notification");
        this.state = {
            searchValue: "",
            suggestions: [],
            loading: false,
        };

        // Handle component errors
        onError((error) => {
            this.notification.add(error.message || "An error occurred", {
                type: "danger",
            });
            browser.console.error(error);
        });

        // Load initial data if needed
        onWillStart(async () => {
            try {
                await this._loadSuggestions();
            } catch (error) {
                this.notification.add(_t("Failed to load suggestions"), {
                    type: "danger",
                });
                browser.console.error("Error loading suggestions:", error);
            }
        });
    }

    /**
     * Load suggestions based on search value
     */
    async _loadSuggestions() {
        try {
            this.state.loading = true;
            const domain = [];
            
            // Add search domain if search value exists
            if (this.state.searchValue) {
                domain.push(['name', 'ilike', this.state.searchValue]);
            }
            
            // Add additional domain from props if any
            if (this.props.domain) {
                domain.push(...this.props.domain);
            }

            // Search for records
            const records = await this.orm.searchRead(
                this.props.resModel,
                domain,
                ['id', 'name', 'lark_guid', 'member_count'],
                { limit: 10 }
            );

            this.state.suggestions = records;
        } catch (error) {
            console.error("Error loading suggestions:", error);
            this.notification.add(
                this.env._t("Error loading tasklists"),
                { type: 'danger' }
            );
        } finally {
            this.state.loading = false;
            this.render();
        }
    }

    /**
     * Handle search input change
     */
    _onSearchInput(ev) {
        this.state.searchValue = ev.target.value;
        this._loadSuggestions();
    }

    /**
     * Handle suggestion selection
     */
    _onSelectSuggestion(suggestion) {
        this.props.onSelect(suggestion);
        this.state.searchValue = '';
        this.state.suggestions = [];
    }
}

// Define the many2one autocomplete field
const many2oneAutocomplete = {
    component: Many2OneAutocomplete,
    extractProps: ({ attrs }) => ({
        'class': attrs.class,
        'placeholder': attrs.placeholder || _t("Search..."),
    }),
};

// Register the component
registry.category("fields").add("many2one_autocomplete", many2oneAutocomplete);

// Export the component
export { many2oneAutocomplete, Many2OneAutocomplete };

// Default export for backward compatibility
export default many2oneAutocomplete;
