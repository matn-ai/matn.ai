from ..tasks import openai_client

def persian_translator(text, llm='gpt-3.5-turbo'):
    prompt = 'translate the text below to persian. Just return the translated Text with HTML tags\nText: `{}`'
    messages = [
        {"role": "assistant", "content": 'You are a professional Persian translator'},
        {"role": "user", "content": prompt.format(text)},
    ]
    
    response = openai_client.chat.completions.create(
        model=llm,
        messages=messages,
        temperature=0.3
    )
    result, usage = response.choices[0].message.content, response.usage
    return result, usage