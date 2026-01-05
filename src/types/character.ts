export interface VoiceConfig {
    provider: string;
    voice_name: string;
}

export interface CharacterProfile {
    id: string;
    name: string;
    description?: string;
    model_id: string;
    persona_id: string;
    voice: VoiceConfig;
}
