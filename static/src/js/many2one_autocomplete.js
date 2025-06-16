/** @odoo-module */

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

const { Component, onWillStart } = owl;

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

        // Load initial data if needed
        onWillStart(async () => {
            await this._loadSuggestions();
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

// Register the component
export const many2oneAutocomplete = {
    component: Many2OneAutocomplete,
    extractProps: ({ attrs }) => ({
        resModel: attrs.options.model,
        domain: attrs.options.domain || [],
        onSelect: attrs.options.on_select || (() => {}),
    }),
};

registry.category("fields").add("many2one_autocomplete", many2oneAutocomplete);
