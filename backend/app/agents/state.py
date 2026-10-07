import operator
from typing import Annotated,TypedDict

class IncidentState(TypedDict):
  incident : str
  evidence : Annotated[list[str],operator.add]
  root_cause : str
  plan : str
  approved : bool
  result : str
  
  

  

  