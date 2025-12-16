export { };

declare global {
    var PIXI: any;

    interface Window {
        pywebview?: {
            api: {
                // Window Management
                close_window: () => void;
                resize_window: (width: number, height: number) => void;
                move_window: (x: number, y: number) => void;
                get_window_pos: () => Promise<{ x: number, y: number }>;
                save_window_position: () => Promise<any>;

                // Settings
                open_settings: () => void;
                get_settings: () => Promise<any>;
                save_settings: (settings: any) => Promise<any>;
                get_voice_types: () => Promise<any>;

                // Chat & Logic
                chat: (message: string) => Promise<any>;
                force_talk: () => Promise<any>;
                suggest_reply: () => Promise<string>;
                get_personas: () => Promise<string[]>;

                // Utils
                get_url_metadata: (url: string) => Promise<{ title: string, image: string | null }>;

                // Calendar
                get_calendar_events: () => Promise<any>;
                get_calendar_status: () => Promise<any>;
                authenticate_calendar: () => Promise<any>;

                // Soul Bubble
                trigger_bubble_action: (actionId: string) => Promise<any>;

                // Debug & History
                debug_log: (message: string) => Promise<any>;
                get_history: (limit: number) => Promise<any[]>;
                restore_history: () => Promise<any[]>;
                dismiss_bubble: (actionId: string) => Promise<any>;
                change_persona: (id: string) => Promise<any>;
            };
        };
    }
}
