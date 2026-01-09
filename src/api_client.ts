// Type definition for PyWebview
/// <reference path="./types.d.ts" />
// Types moved to types.d.ts

export class ApiClient {
    private isDesktop: boolean;

    constructor() {
        // Simple detection: does window.pywebview exist?
        // Note: pywebview might take a moment to inject. 
        // We usually wait for 'pywebviewready' event in main code, 
        // but methods are called after load usually.
        this.isDesktop = false; // Will check on each call or init?
        // Better to check dynamically or listen to event.
        // Let's check dynamically for robustness.
    }

    private get desktopApi() {
        return (window as any).pywebview?.api;
    }

    /**
     * Send chat message
     */
    async chat(text: string, image_data?: string): Promise<any> {
        if (this.isDesktop || (window as any).pywebview) {
            return await (window as any).pywebview.api.chat(text, image_data);
        } else {
            const res = await fetch('/api/chat', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ text: text, image_data: image_data })
            });
            return await res.json();
        }
    }

    async take_screenshot_for_preview(): Promise<any> {
        if (this.desktopApi && this.desktopApi.take_screenshot_for_preview) {
            return await this.desktopApi.take_screenshot_for_preview();
        }
        return { status: "error", message: "Not supported" };
    }

    async chat_with_vision(text: string, mode: string = "screen"): Promise<any> {
        if (this.isDesktop || (window as any).pywebview) {
            return await (window as any).pywebview.api.chat_with_vision(text, mode);
        } else {
            // Web fallback? Maybe upload image or not supported?
            console.warn("Vision not supported in Web Mode");
            return { text: "Web版では視覚機能はサポートされていません。" };
        }
    }

    // ★このメソッドがないとピンクボタンは動きません！
    async force_talk(): Promise<any> {
        if (this.isDesktop || (window as any).pywebview) {
            return await (window as any).pywebview.api.force_talk();
        } else {
            const res = await fetch('/api/force_talk', {
                method: 'POST'
            });
            return await res.json();
        }
    }

    /**
     * Get Calendar Events
     */
    async get_upcoming_events(): Promise<any> {
        if (this.desktopApi) {
            // Note: Old api was get_calendar_events? No, check index.ts usage.
            // Currently index.ts uses api.chat? Wait, calendar logic is inside chat for intent.
            // But Settings uses get_calendar_status.
            // Let's implement generic mapping.
            return []; // Placeholder
        } else {
            const res = await fetch('/api/calendar');
            return await res.json();
        }
    }

    // ... Implement other methods as needed, or fallback to mock ...
    // For Chat basic functionality, 'chat' is the main one.

    // Need explicit support for settings?
    async get_settings(): Promise<any> {
        if (this.desktopApi) {
            return await this.desktopApi.get_settings();
        } else {
            // Web Mode: Fetch from server
            try {
                const res = await fetch('/api/settings');
                if (res.ok) return await res.json();
            } catch (e) {
                console.error("Failed to fetch settings:", e);
            }
            return {};
        }
    }

    async save_settings(settings: any): Promise<any> {
        if (this.desktopApi) {
            // Desktop usually saves via separate calls or generic save?
            // Existing Desktop likely uses specific setters or a save method.
            // Let's check update_settings or similar if it exists.
            // If not, we might fall back or assume it's `save_settings` if we added it to Mixin.
            // Checking task.md Phase 6: "Verify API Key persistence".
            // Likely `save_settings` exists.
            if (this.desktopApi.save_settings) {
                return await this.desktopApi.save_settings(settings);
            }
            // Fallback: Desktop might rely on individual calls within Settings Logic?
            // But we want unified. Let's assume save_settings exists or we added it.
            return { status: "ok" };
        } else {
            // Web Mode
            try {
                const res = await fetch('/api/settings', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(settings)
                });
                return await res.json();
            } catch (e) {
                console.error("Save Settings Error:", e);
                return { error: e };
            }
        }
    }

    async get_voice_types(provider: string = 'voicevox'): Promise<any> {
        if (this.desktopApi) return await this.desktopApi.get_voice_types(provider);
        try {
            const res = await fetch(`/api/voice_types?provider=${provider}`);
            if (res.ok) return await res.json();
        } catch (e) {
            console.error("Failed to fetch voice types:", e);
        }
        return [];
    }

    async get_calendar_status(): Promise<any> {
        if (this.desktopApi) return await this.desktopApi.get_calendar_status();
        return false;
    }

    // --- Character API ---
    async get_character_profiles(): Promise<any[]> {
        if (this.desktopApi && this.desktopApi.get_character_profiles) {
            return await this.desktopApi.get_character_profiles();
        } else {
            try {
                const res = await fetch('/api/character/profiles');
                if (res.ok) return await res.json();
            } catch (e) {
                console.error("Failed to fetch character profiles:", e);
            }
            return [];
        }
    }

    // --- Persona System ---
    async getPersonas(): Promise<string[]> {
        if (this.desktopApi) {
            return await this.desktopApi.get_persona_list();
        } else {
            try {
                const res = await fetch('/api/personas');
                if (res.ok) return await res.json();
            } catch (e) {
                console.error("Failed to fetch personas:", e);
            }
            return [];
        }
    }

    async changePersona(personaId: string): Promise<any> {
        if (this.desktopApi) {
            return await this.desktopApi.change_persona(personaId);
        } else {
            try {
                const res = await fetch('/api/persona/change', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ persona_id: personaId })
                });
                return await res.json();
            } catch (e) {
                console.error("Failed to change persona:", e);
                return { status: "error", message: e };
            }
        }
    }

    // --- Soul Bubble ---
    async trigger_bubble_action(actionId: string): Promise<any> {
        if (this.desktopApi) {
            return await this.desktopApi.trigger_bubble_action(actionId);
        } else {
            console.warn("Soul Bubble not supported in Web Mode yet (or implement endpoint)");
            return { status: "ignored" }; // Fallback
        }
    }

    async dismiss_bubble(actionId: string): Promise<any> {
        if (this.desktopApi && this.desktopApi.dismiss_bubble) {
            return await this.desktopApi.dismiss_bubble(actionId);
        }
        return { status: "ignored" };
    }

    // --- History ---
    async get_history(limit: number = 50): Promise<any[]> {
        if (this.desktopApi && this.desktopApi.get_history) {
            return await this.desktopApi.get_history(limit);
        } else {
            try {
                const res = await fetch(`/api/history?limit=${limit}`);
                if (res.ok) return await res.json();
            } catch (e) {
                console.error("Failed to fetch history:", e);
            }
            return [];
        }
        return [];
    }

    async restore_history(): Promise<any[]> {
        if (this.desktopApi && this.desktopApi.restore_history) {
            return await this.desktopApi.restore_history();
        } else {
            try {
                const res = await fetch('/api/history/restore');
                if (res.ok) return await res.json();
            } catch (e) {
                console.error("Failed to restore history:", e);
            }
            return [];
        }
    }

    async generate_bubble(): Promise<any> {
        if (this.desktopApi && this.desktopApi.generate_bubble) {
            return await this.desktopApi.generate_bubble();
        } else {
            // Web Mock
            return {
                category: 'topics',
                text: 'Web Mock Topic',
                action_id: 'MOCK_' + Date.now(),
                type: 'discovery'
            };
        }
    }

    async get_topic_suggestions(): Promise<string[]> {
        if (this.desktopApi && this.desktopApi.get_topic_suggestions) {
            return await this.desktopApi.get_topic_suggestions();
        } else {
            try {
                const res = await fetch('/api/topics/suggestions');
                if (res.ok) return await res.json();
            } catch (e) { console.error(e); }
            return ["Topics API Error"];
        }
    }

    // --- History API (Step 4) ---
    async get_sessions(): Promise<any[]> {
        if (this.desktopApi && this.desktopApi.get_sessions) {
            return await this.desktopApi.get_sessions();
        } else {
            // Web Fetch
            try {
                const res = await fetch('/api/history/sessions');
                if (res.ok) return await res.json();
            } catch (e) { console.error(e); }
            return [];
        }
    }

    async get_session_detail(id: number): Promise<any> {
        if (this.desktopApi && this.desktopApi.get_session_detail) {
            return await this.desktopApi.get_session_detail(id);
        } else {
            try {
                const res = await fetch(`/api/history/${id}`);
                if (res.ok) return await res.json();
            } catch (e) { console.error(e); }
            return {};
        }
    }

    async resume_session(id: number): Promise<any> {
        if (this.desktopApi && this.desktopApi.resume_session) {
            return await this.desktopApi.resume_session(id);
        } else {
            try {
                const res = await fetch(`/api/history/${id}/resume`, { method: 'POST' });
                if (res.ok) return await res.json();
            } catch (e) { console.error(e); }
            return {};
        }
    }

    async manual_save_session(): Promise<any> {
        if (this.desktopApi && this.desktopApi.manual_save_session) {
            return await this.desktopApi.manual_save_session();
        }
        return { status: "ignored" };
    }

    async start_new_session(): Promise<any> {
        if (this.desktopApi && this.desktopApi.start_new_session) {
            return await this.desktopApi.start_new_session();
        }
        return { status: "ignored" };
    }

    // --- Proactive Mode ---
    async toggle_proactive(enabled: boolean): Promise<any> {
        if (this.desktopApi && this.desktopApi.toggle_proactive) {
            return await this.desktopApi.toggle_proactive(enabled);
        }
        return { status: "ignored" };
    }

    async force_proactive(): Promise<any> {
        if (this.desktopApi && this.desktopApi.force_proactive) {
            return await this.desktopApi.force_proactive();
        }
        return { status: "ignored" };
    }

    // --- Vision Target API ---
    async start_target_drag(): Promise<any> {
        if (this.desktopApi && this.desktopApi.start_target_drag) {
            return await this.desktopApi.start_target_drag();
        } else {
            console.warn("Vision Target Drag not supported in Web Mode");
            return { status: "ignored" };
        }
    }

    async clear_vision_target(): Promise<any> {
        if (this.desktopApi && this.desktopApi.clear_vision_target) {
            return await this.desktopApi.clear_vision_target();
        }
        return { status: "ignored" };
    }
}

export const api = new ApiClient();
