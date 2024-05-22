from ednaresults import OccurrenceBuilder
import logging
from dotenv import load_dotenv


load_dotenv()
logger = logging.getLogger(__name__)
logging.basicConfig(format="%(asctime)s %(message)s", level=logging.INFO)


occurrence_builder = OccurrenceBuilder()
occurrence_builder.build()
# builder.upload()