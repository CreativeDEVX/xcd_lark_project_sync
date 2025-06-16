/** @odoo-module alias=lark_project_sync.systray **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Component, useState, useRef, onMounted, xml } from "@odoo/owl";
import { useErrorHandlers } from "@web/core/errors/error_handler_hook";

class LarkProjectSyncSystray extends Component {
    static template = xml`
        <div class="o_mail_systray_item o_lark_sync_systray" t-ref="dropdown">
            <a href="#" class="o_lark_sync_icon" t-on-click="toggleDropdown" title="Lark Sync">
                <i class="fa fa-refresh" t-att-class="{'fa-spin': state.isLoading}" />
            </a>
            <t t-if="state.isOpen" class="o_dropdown_menu">
                <div class="lark-sync-header">
                    <a href="#" class="dropdown-item" t-on-click="syncWithLark">
                        <i class="fa fa-refresh"/> Sync Now
                    </a>
                </div>
                <div class="lark-sync-logs" t-if="state.logMessages.length">
                    <div class="log-header">Synchronization Logs</div>
                    <div class="log-entries">
                        <t t-foreach="state.logMessages" t-as="log" t-key="log_index">
                            <div class="log-entry" t-att-class="{
                                'text-success': log.includes('[success]'),
                                'text-danger': log.includes('failed') || log.includes('error'),
                                'text-muted': log.includes('[debug]')
                            }">
                                <i t-att-class="{
                                    'fa fa-check text-success': log.includes('[success]'),
                                    'fa fa-times text-danger': log.includes('failed') || log.includes('error'),
                                    'fa fa-info-circle': log.includes('[info]') && !log.includes('success') && !log.includes('failed'),
                                    'fa fa-bug text-muted': log.includes('[debug]')
                                }"></i>
                                <span t-esc="log"/>
                            </div>
                        </t>
                    </div>
                </div>
            </t>
        </div>
    `;

    setup() {
        this.state = useState({
            isOpen: false,
            isLoading: false,
            logMessages: []
        });
        this.dropdownRef = useRef("dropdown");
        
        // Initialize services in setup
        this.rpc = useService("rpc");
        this.notification = useService("notification");
        this.rpcService = useService("rpc");
        
        // Logging function
        this.log = (message, type = 'info') => {
            const timestamp = new Date().toISOString().substr(11, 8);
            const logEntry = `[${timestamp}] ${message}`;
            this.state.logMessages = [logEntry, ...this.state.logMessages].slice(0, 50); // Keep last 50 messages
            console.log(`[LarkSync] ${logEntry}`);
            return logEntry;
        };
        
        // Create a safe RPC wrapper
        this.safeRPC = {
            route: async (route, params = {}) => {
                try {
                    return await this.rpcService(route, params);
                } catch (e) {
                    console.error("RPC call failed:", e);
                    throw e;
                }
            }
        };
        
        // Create a safe notification wrapper
        this.safeNotification = {
            add: (message, options = {}) => {
                try {
                    return this.notification.add(message, options);
                } catch (e) {
                    console[options.type === "danger" ? "error" : "log"](message);
                }
            }
        };

        // Close dropdown when clicking outside
        onMounted(() => {
            const handleClickOutside = (event) => {
                if (this.dropdownRef.el && !this.dropdownRef.el.contains(event.target)) {
                    this.state.isOpen = false;
                }
            };
            document.addEventListener('mousedown', handleClickOutside);
            return () => document.removeEventListener('mousedown', handleClickOutside);
        });
    }

    toggleDropdown(event) {
        event.preventDefault();
        this.state.isOpen = !this.state.isOpen;
    }

    async syncWithLark(event) {
        event.preventDefault();
        event.stopPropagation();
        
        const startTime = new Date();
        this.state.isLoading = true;
        this.log("Starting synchronization process...", 'info');
        
        try {
            this.log("Initiating RPC call to sync endpoint", 'debug');
            const result = await this.safeRPC.route("/lark_project_sync/sync", {});
            
            const duration = (new Date() - startTime) / 1000;
            const successMsg = `Synchronization completed successfully in ${duration.toFixed(2)} seconds`;
            
            this.log(successMsg, 'success');
            this.safeNotification.add(successMsg, { 
                type: "success",
                sticky: false
            });
            
            if (result) {
                this.log(`Sync result: ${JSON.stringify(result)}`, 'debug');
            }
            
            this.state.isOpen = true; // Keep dropdown open to show logs
            return result;
            
        } catch (error) {
            const errorMsg = `Synchronization failed: ${error.message || 'Unknown error'}`;
            this.log(errorMsg, 'error');
            console.error("Error during synchronization:", error);
            
            this.safeNotification.add(errorMsg, { 
                type: "danger",
                sticky: true
            });
            
            this.state.isOpen = true; // Keep dropdown open to show error logs
            throw error;
            
        } finally {
            this.state.isLoading = false;
        }
    }
}

// Register the systray item
export const systrayItem = {
    Component: LarkProjectSyncSystray,
};

// Register the component in the systray category
registry.category("systray").add("lark_project_sync.systray_item", systrayItem, { sequence: 100 });
