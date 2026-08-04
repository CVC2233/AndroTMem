def meituan_waimai_shopping_prompt(quantity, item_name, store_name=None, specs=None):
    prompt = f'Specifically, you need to purchase "{quantity}" unit(s) of "{item_name}"'
    
    if store_name:
        prompt += f' from "{store_name}"'
        
    prompt += ' by performing a series of actions'

    if specs:
        prompt += f', and ensure that the specifications are: "{specs}"'

    prompt += '.'
    return prompt
def chat_test_prompt(test):
    return f"test---{test}"
