import os
import requests
import json

class BhashiniClient:
    def __init__(self):
        self.api_key = os.getenv("BHASHINI_API_KEY", "").strip()
        self.user_id = os.getenv("BHASHINI_USER_ID", "").strip()
        self.pipeline_id = os.getenv("BHASHINI_PIPELINE_ID", "").strip()
        self.auth_url = os.getenv("BHASHINI_AUTH_URL", "https://meity-auth.ulcacontrib.org/ulca/apis/v0/model/getModelsPipeline")
        self.inference_base_url = os.getenv("BHASHINI_INFERENCE_URL", "https://dhruva-api.bhashini.gov.in/services/inference/pipeline")
        
    def is_configured(self) -> bool:
        return bool(self.api_key and self.user_id and self.pipeline_id)

    def call_translation_pipeline(self, text: str, source_lang: str, target_lang: str) -> dict:
        """Calls official Bhashini ULCA / Dhruva pipeline if credentials are configured."""
        if not self.is_configured():
            return {"success": False, "error": "Bhashini credentials not configured in .env"}
            
        headers = {
            "userID": self.user_id,
            "ulcaApiKey": self.api_key,
            "Content-Type": "application/json"
        }
        
        payload = {
            "pipelineTasks": [
                {
                    "taskType": "translation",
                    "config": {
                        "language": {
                            "sourceLanguage": source_lang,
                            "targetLanguage": target_lang
                        }
                    }
                }
            ],
            "inputData": {
                "input": [{"source": text}]
            }
        }
        
        try:
            resp = requests.post(self.inference_base_url, json=payload, headers=headers, timeout=8.0)
            if resp.status_code == 200:
                data = resp.json()
                # Parse response
                tasks = data.get("pipelineResponse", [])
                for task in tasks:
                    if task.get("taskType") == "translation":
                        output_list = task.get("output", [])
                        if output_list and "target" in output_list[0]:
                            return {"success": True, "translated_text": output_list[0]["target"]}
                return {"success": False, "error": "Unexpected response format from Bhashini"}
            else:
                return {"success": False, "error": f"Bhashini HTTP {resp.status_code}: {resp.text}"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def call_tts_pipeline(self, text: str, language: str, gender: str = "female") -> dict:
        """Calls official Bhashini TTS pipeline if credentials configured."""
        if not self.is_configured():
            return {"success": False, "error": "Bhashini credentials not configured"}
            
        headers = {
            "userID": self.user_id,
            "ulcaApiKey": self.api_key,
            "Content-Type": "application/json"
        }
        payload = {
            "pipelineTasks": [
                {
                    "taskType": "tts",
                    "config": {
                        "language": {"sourceLanguage": language},
                        "gender": gender
                    }
                }
            ],
            "inputData": {
                "input": [{"source": text}]
            }
        }
        try:
            resp = requests.post(self.inference_base_url, json=payload, headers=headers, timeout=8.0)
            if resp.status_code == 200:
                data = resp.json()
                for task in data.get("pipelineResponse", []):
                    if task.get("taskType") == "tts":
                        audio_list = task.get("audio", [])
                        if audio_list and "audioContent" in audio_list[0]:
                            return {"success": True, "audio_content": audio_list[0]["audioContent"]}
            return {"success": False, "error": "TTS generation failed"}
        except Exception as e:
            return {"success": False, "error": str(e)}
