SHOPPING_QUESTION_PROMPT="""<image>
You need to complete a "{task_type}" task in the "{app_name}" application. Specifically, you need to purchase "{quantity}" unit(s) of "{item_name}" from "{store_name}" by performing a series of actions by performing a series of actions, and ensure that the specifications are: "{specs}.
"""
# Top-level task definition prompt
TASK_DEFINITION_PROMPT = """You need to complete a "{task_type}" task in the "{app_name}" application. """
#----------------------------------------------------------

# , and ensure that the specifications are: "{specs}"
MEITUAN_SHOPPING_PROMPT_SHORT = """Specifically, you need to purchase "{quantity}" unit(s) of "{item_name}" from "{store_name}" by performing a series of actions.
"""