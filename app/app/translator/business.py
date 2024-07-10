from ..tasks import openai_client

def persian_translator(text, llm='gpt-3.5-turbo'):
    prompt = (
        'translate the text below to persian. Just return the translated Text with html <p> tags\n',
        'Use <ul> and <li> for bullet points in the text.\n',
        f'Text: `{text}`'
    )
    messages = [
        {"role": "assistant", "content": 'You are a professional Persian translator. Do not translate the page number, page headers and footers. Just return the translated text'},
        {"role": "user", "content": ''.join(prompt)},
    ]
    
    response = openai_client.chat.completions.create(
        model=llm,
        messages=messages,
        temperature=0.1
    )
    result, usage = response.choices[0].message.content, response.usage
    return result, usage