import datetime

AUDIT_LOG : list[dict] = []

ALLOWED_WRITE_ACTIONS = {"rollback","restart"}
FORBIDDEN = {"delete_database","drop_table"}


def execute_action(action:str,target:str,user_role:str,approved:bool):
  if action in FORBIDDEN:
    raise PermissionError(f"{action} is not allowed")
  
  if action not in ALLOWED_WRITE_ACTIONS:
    raise PermissionError(f"Unknown action {action}")
  
  if user_role not in ("sre","admin"):
    raise PermissionError("User not authorized for write action")
  
  if not approved:
    raise PermissionError("Human approved required")
  
  AUDIT_LOG.append({"time":datetime.datetime.utcnow().isoformat(),
                    "action":action,"target":target,"role":user_role})
  
  return f"Executed {action} on {target}"
    
  
  
    
  
