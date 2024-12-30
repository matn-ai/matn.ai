

'''
2000-19999-20T
20000-39999-19T
40000-59999-18T
60000-79999-17T
80000-100000-16T
'''

RATIO1 = 3
RATIO2 = 2.9
RATIO3 = 2.8
RATIO4 = 2.7
RATIO5 = 2.5


def calculate_charge_rule(rial_amount):
    if rial_amount < 20_000 * RATIO1:
        return rial_amount // RATIO1
    elif rial_amount < 40_000 * RATIO2:
        return rial_amount // RATIO2
    elif rial_amount < 60_000 * RATIO2:
        return rial_amount // RATIO2
    elif rial_amount < 80_000 * RATIO4:
        return rial_amount // RATIO4
    else:
        return rial_amount // RATIO5
    
    return rial_amount // RATIO1



MODELS_RATIO = {
    'claude-3-haiku': 1,
    'claude-3.5-haiku': 1.5,
    'gpt-3.5': 1,
    'gemini-pro-1.5': 3,
    'claude-3.5-sonnet': 5,
    'gpt-4o': 5,
    'claude-3-opus': 25,
    'gemini-flash-1.5': 1,
    'gpt-4': 20,
    'gpt-4-turbo': 10,
    'o1-mini': 4,
    'o1-preview': 5,
    'gpt-4o-mini': 1.5,
    'gpt-3.5-turbo': 1,
    'codellama-70b-instruct': 1,
    'dolphin-mixtral-8x22b': 1.5,
    'llama-3-sonar-large-32k-online': 1.5,
    'llama-3-sonar-small-32k-online': 1.5,
}

def calculate_reduce_charge(total_words, model='gpt-4o-mini'):
    ratio = 5
    if model in MODELS_RATIO:
        ratio = MODELS_RATIO[model]
    if 'free' in model:
        ratio = 0
    total_words = total_words * ratio
    
    return total_words