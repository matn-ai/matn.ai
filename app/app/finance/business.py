

'''
2000-19999-20T
20000-39999-19T
40000-59999-18T
60000-79999-17T
80000-100000-16T
'''


def calculate_charge_rule(amount):
    if amount < 19999:
        return amount // 20
    elif amount < 39999:
        return amount // 19
    elif amount < 59999:
        return amount // 18
    elif amount < 79999:
        return amount // 17
    elif amount < 100000:
        return amount // 16
    
    return amount // 20



MODELS_RATIO = {
    'gpt-4o': 3,
    'gpt-3.5': 1,
    'gpt-3.5-turbo': 1
}

def calculate_reduce_charge(total_words, model='gpt-3.5-turbo'):
    ratio = MODELS_RATIO[model]
    total_words = total_words * ratio
    
    return total_words