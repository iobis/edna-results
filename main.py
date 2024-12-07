from ednaresults import OccurrenceBuilder
from ednaresults.lists import ListGenerator
import logging
from dotenv import load_dotenv


load_dotenv()
logger = logging.getLogger(__name__)
logging.basicConfig(format="%(asctime)s %(levelname)s %(message)s", level=logging.INFO)


list_generator = ListGenerator()
occurrence_builder = OccurrenceBuilder(
    list_generator=list_generator,
    sync_results=False
)
occurrence_builder.build()
