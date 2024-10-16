

'''
2000-19999-20T
20000-39999-19T
40000-59999-18T
60000-79999-17T
80000-100000-16T
'''


def calculate_charge_rule(rial_amount):
    if rial_amount < 20_000 * 15:
        return rial_amount // 15
    elif rial_amount < 40_000 * 14:
        return rial_amount // 14
    elif rial_amount < 60_000 * 13:
        return rial_amount // 13
    elif rial_amount < 80_000 * 12:
        return rial_amount // 12
    elif rial_amount < 100_000 * 12:
        return rial_amount // 10
    
    return rial_amount // 10



MODELS_RATIO = {
    'gpt-4o': 5,
    'gpt-4': 20,
    'gpt-4-turbo': 10,
    'o1-mini': 3,
    'o1-preview': 5,
    'gpt-4o-mini': 1.5,
    'gpt-3.5': 1,
    'claude-3.opus': 10,
    'gpt-3.5-turbo': 1,
    'claude-3-haiku': 1,
    'claude-3.5-sonnet': 4,
    'gemini-pro-1.5': 3,
    'codellama-70b-instruct': 1,
    'dolphin-mixtral-8x22b': 1.5,
    'llama-3-sonar-large-32k-online': 1.5,
    'llama-3-sonar-small-32k-online': 1.5,
}

def calculate_reduce_charge(total_words, model='gpt-3.5-turbo'):
    ratio = 5
    if model in MODELS_RATIO:
        ratio = MODELS_RATIO[model]
    if 'free' in model:
        ratio = 0
    total_words = total_words * ratio
    
    return total_words