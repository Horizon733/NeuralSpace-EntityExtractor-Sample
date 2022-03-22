import logging
import os
from typing import Dict, Any, Optional, List

import requests
import rasa
from rasa.nlu.extractors.extractor import EntityExtractor
from rasa.nlu.config import RasaNLUModelConfig
from rasa.nlu.model import Metadata
from rasa.shared.constants import DOCS_URL_COMPONENTS
from rasa.shared.importers import rasa
from rasa.shared.nlu.constants import TEXT, ENTITIES
from rasa.shared.nlu.training_data.message import Message
from typing_extensions import Text

"""
step 1: detect language of latest message
step 2: translate latest message to english if not in english
step 3: provide response for the same in detected language
step 4: wait for user reply and start with step 1
"""

logger = logging.getLogger(__name__)


def extract_value(match: Dict[Text, Any]) -> Dict[Text, Any]:
    if match["value"].get("type") == "interval":
        value = {
            "to": match["value"].get("to", {}).get("value"),
            "from": match["value"].get("from", {}).get("value"),
        }
    else:
        value = match["value"].get("value")

    return value


def convert_neuralspace_format_to_rasa(
        matches: List[Dict[Text, Any]]
) -> List[Dict[Text, Any]]:
    extracted = []

    for match in matches["data"]["entities"]:
        entity = {
            "start": match["start_idx"],
            "end": match["end_idx"],
            "text": match.get("body", match.get("text", None)),
            "value": match["value"],
            "confidence": 1.0,
            "additional_info": match["value"],
            "entity": match["type"],
        }

        extracted.append(entity)

    return extracted


class NeuralSpaceEntityExtractor(EntityExtractor):
    defaults = {
        "language": "en",
        "access_token": None,
        "dimension": None,
        "timeout": 3
    }

    def __init__(
            self,
            component_config: Optional[Dict[Text, Any]] = None,
            language: Optional[Text] = None
    ) -> None:
        super().__init__(component_config)
        self.language = language
        self.headers = {
            "authorization": component_config["access_token"],
        }

    @classmethod
    def create(
            cls, component_config: Dict[Text, Any], config: RasaNLUModelConfig
    ) -> "NeuralSpaceEntityExtractor":
        return cls(component_config, config.language)

    def _access_token(self) -> Optional[Text]:
        if os.environ.get("NEURALSPACE_ACCESS_TOKEN"):
            return os.environ["NEURALSPACE_ACCESS_TOKEN"]
        return self.component_config.get("access_token")

    def _payload(self, text: Text) -> Dict[Text, Any]:
        language = self.component_config["language"]
        return {
            "text": text,
            "language": language,
        }

    def _neuralspace_parse(self, text: Text) -> List[Dict[Text, Any]]:
        translate_url = "https://platform.neuralspace.ai/api/ner/v1/entity"
        try:
            payload = self._payload(text)
            response = requests.post(
                url=translate_url,
                data=payload,
                headers=self.headers,
                timeout=self.component_config.get("timeout")
            )
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(
                    f"Failed to get a proper response from remote "
                    f"translation at '{translate_url}. "
                    f"Status Code: {response.status_code}. "
                    f"Response: {response.text}"
                )
                return []
        except(
                requests.exceptions.ConnectionError,
                requests.exceptions.ReadTimeout,
        ) as e:
            logger.error(
                "Failed to connect to neuralspace https endpoint. Make sure "
                "the url is running/healthy/not stale and the proper host "
                "and port are set in the configuration. More "
                "information on how to run the server can be found on "
                "Error: {}".format(e)
            )

    def process(self, message: Message, **kwargs: Any) -> Message:
        if self._access_token() is None:
            rasa.shared.utils.io.raise_warning(
                "NeuralSpace Entity Extractor component in pipeline, but no "
                "`url` configuration in the config "
                "file nor is `ACCESS TOKEN` "
                "set as an environment variable. No entities will be extracted!",
                docs=DOCS_URL_COMPONENTS + "#NeuralSpaceEntityExtractor",
            )
            return message
        matches = self._neuralspace_parse(message.get(TEXT))
        all_extracted = convert_neuralspace_format_to_rasa(matches)
        extracted = self.filter_irrelevant_entities(all_extracted, self.component_config["dimensions"])
        extracted = self.add_extractor_name(extracted)
        message.set(
            ENTITIES, message.get(ENTITIES, []) + extracted, add_to_output=True
        )
        return message

    @classmethod
    def load(
            cls,
            meta: Dict[Text, Any],
            model_dir: Text,
            model_metadata: Optional[Metadata] = None,
            cached_component: Optional["NeuralSpaceEntityExtractor"] = None,
            **kwargs: Any,
    ) -> "NeuralSpaceEntityExtractor":
        """Loads trained component (see parent class for full docstring)."""
        language = model_metadata.get("language") if model_metadata else None
        return cls(meta, language)
