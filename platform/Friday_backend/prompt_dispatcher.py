# prompt_dispatcher.py

from prompt_templates import TASK_DEFINITION_PROMPT
from app_prompts.meituan_waimai_prompts import meituan_waimai_shopping_prompt,chat_test_prompt
# ... 可继续扩展

PROMPT_ROUTER = {
    ("meituan_waimai", "shopping"): meituan_waimai_shopping_prompt,
    ("wechat","chat"):chat_test_prompt
    
}

def get_task_prompt(app_name, task_type, **kwargs):
    intro = TASK_DEFINITION_PROMPT.format(task_type=task_type, app_name=app_name)

    key = (app_name.lower(), task_type.lower())
    if key not in PROMPT_ROUTER:
        raise ValueError(f"No prompt template defined for task ({task_type}) in app ({app_name})")
    
    prompt_func = PROMPT_ROUTER[key]
    task_specific_part = prompt_func(**kwargs)
    
    return intro + task_specific_part
