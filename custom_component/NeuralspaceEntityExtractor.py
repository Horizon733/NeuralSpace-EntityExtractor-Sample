import logging
import os
from typing import Dict, Any, Optional, List

import requests
import rasa
from rasa.engine.graph import GraphComponent, ExecutionContext
from rasa.engine.recipes.default_recipe import DefaultV1Recipe
from rasa.engine.storage.resource import Resource
from rasa.engine.storage.storage import ModelStorage
from rasa.nlu.extractors.extractor import EntityExtractorMixin
from rasa.shared.constants import DOCS_URL_COMPONENTS
from rasa.shared.importers import rasa
from rasa.shared.nlu.constants import TEXT, ENTITIES
from rasa.shared.nlu.training_data.message import Message
from typing_extensions import Text


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


@DefaultV1Recipe.register(
    DefaultV1Recipe.ComponentType.ENTITY_EXTRACTOR, is_trainable=False
)
class NeuralSpaceEntityExtractor(GraphComponent, EntityExtractorMixin):
    """Searches for structured entities, e.g. dates, using a neuralspace server."""

    @staticmethod
    def get_default_config() -> Dict[Text, Any]:
        return {
            # default language `en` so entity extractor works
            "language": "en",
            # access token need to be provided for entity extractor to work
            "access_token": None,
            # by default all dimensions recognized by neuralspace are returned
            # dimensions can be configured to contain an array of strings
            # with the names of the dimensions to filter for
            "dimension": None,
            # Timeout for receiving response from HTTP URL of the running
            # neuralspace server. If not set the default timeout of duckling HTTP URL
            # is set to 3 seconds.
            "timeout": 3
        }

    def __init__(
            self,
            config: Dict[Text, Any]
    ) -> None:
        self.component_config = config

    @classmethod
    def create(
            cls,
            config: Dict[Text, Any],
            model_storage: ModelStorage,
            resource: Resource,
            execution_context: ExecutionContext,
    ) -> "NeuralSpaceEntityExtractor":
        return cls(config)

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
        """
        Sends text message to Neuralspace endpoint with access token.
        Neuralspace provides json response with entities extracted.
        """
        translate_url = "https://platform.neuralspace.ai/api/ner/v1/entity"
        headers = {
            "authorization": self.component_config["access_token"],
        }
        try:
            payload = self._payload(text)
            response = requests.post(
                url=translate_url,
                data=payload,
                headers=headers,
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

    def process(self, messages: List[Message]) -> List[Message]:
        if self._access_token() is None:
            rasa.shared.utils.io.raise_warning(
                "NeuralSpace Entity Extractor component in pipeline, but no "
                "`url` configuration in the config "
                "file nor is `ACCESS TOKEN` "
                "set as an environment variable. No entities will be extracted!",
                docs=DOCS_URL_COMPONENTS + "#NeuralSpaceEntityExtractor",
            )
            return messages
        for message in messages:
            matches = self._neuralspace_parse(message.get(TEXT))
            all_extracted = convert_neuralspace_format_to_rasa(matches)
            extracted = self.filter_irrelevant_entities(all_extracted, self.component_config["dimensions"])
            extracted = self.add_extractor_name(extracted)
            message.set(
                ENTITIES, message.get(ENTITIES, []) + extracted, add_to_output=True
            )
        return messages
