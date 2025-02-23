import asyncio
import re
import json
import base64
from urllib.parse import quote_plus, parse_qs, urlparse
from bs4 import BeautifulSoup as BS
import aiohttp
from Cryptodome.Cipher import AES
from pprint import pp

BASE_URL="https://asianbxkiun.pro"

async def main():
    res = await asian_search("yuru camp")
    ep_links = await fetch_ep_links(res[0])
    stream = await fetch_stream_link(ep_links[0])
    pp(res)
    pp(ep_links)
    pp(stream)

# flow
async def asian_search(keyword: str):
    '''
    search for drama based on a keyword
    '''
    # url encode search keyword
    search_key = quote_plus(keyword)
    search_url = f"{BASE_URL}/search.html?keyword={search_key}"
    res = await req(search_url)
    soup = BS(res, "html.parser")

    # Get basic details available from the site
    links = soup.select("ul.items li a")[:10] # search_limit
    titles = soup.select('div.name')
    last_ep_dates = soup.select('div.meta span')

    search_results = []
    # get matched items. Limit the search results to be displayed.
    for s_link, s_title, s_last_ep_date in zip(links, titles, last_ep_dates):
        link = s_link['href']
        if link.startswith('/'):
            link = BASE_URL + link

        title = ' '.join(s_title.text.strip().split()[:-2])
        last_ep = s_title.text.strip().split()[-1]
        last_ep_date = s_last_ep_date.text.strip()

        # Add mandatory information
        item = {
            'title': title, 'link': link,
            'last_episode': last_ep, 'last_episode_time': last_ep_date
        }
        
        # Add index to every search result
        search_results.append(item)

    return search_results

async def fetch_ep_links(search_result):
    '''
    fetch episode links as dict containing link, name, upload time
    '''
    all_episodes_list = []
    series_link = search_result.get('link')
    res = await req(series_link)
    soup = BS(res, "html.parser")
    all_episodes_list.extend(get_episodes_list(soup))

    return all_episodes_list[::-1] # return episodes in ascending

async def fetch_stream_link(episode):
    link = await get_stream_link(episode.get('episodeLink'), "div.play-video iframe")
    if not link: return
    gdl_config = {
        'link': link,
        'encryption_key': b'93422192433952489752342908585752',
        'decryption_key': b'93422192433952489752342908585752',
        'iv': b'9262859232435825',
        'encrypted_url_args_regex': re.compile(rb'data-value="(.+?)"'),
        'download_fetch_link': "encrypt-ajax.php"
    }
    m3u8_links = await get_download_sources(**gdl_config)
    if 'error' not in m3u8_links:
        for download_link in m3u8_links:
            dlink = download_link.get('file')
            return await parse_m3u8_links(dlink)
    print(m3u8_links["error"])

# utils
async def parse_m3u8_links(master_m3u8_link):
    '''
    parse master m3u8 data and return dict of resolutions and m3u8 links
    '''
    m3u8_links = []
    base_url = '/'.join(master_m3u8_link.split('/')[:-1])
    master_m3u8_data = await req(master_m3u8_link, return_type='text')
    print(f'Master m3u8 data: {master_m3u8_data}')

    _regex_list = lambda data, rgx, grp: [ url.group(grp) for url in re.finditer(rgx, data) ]
    _full_link = lambda link: link if link.startswith('http') else base_url + '/' + link
    resolutions = _regex_list(master_m3u8_data, r'RESOLUTION=(\d+x\d+)', 1)
    resolution_names = _regex_list(master_m3u8_data, 'NAME="(.*)"', 1)
    if len(resolution_names) == 0:
        resolution_names = [ res.lower().split('x')[-1] for res in resolutions ]
    resolution_links = _regex_list(master_m3u8_data, '(.*)m3u8', 0)
    print(f'Resolutions data: {resolutions}, {resolution_names}, {resolution_links}')

    if len(resolution_links) == 0:
        # check for original keyword in the link, or if '#EXT-X-ENDLIST' in m3u8 data
        master_is_child = re.search('#EXT-X-ENDLIST', master_m3u8_data)
        if 'original' in master_m3u8_link or master_is_child:
            m3u8_links.append({
                'downloadLink': master_m3u8_link,
            })

        return m3u8_links

    for _res, _pixels, _link in zip(resolution_names, resolutions, resolution_links):
        # prepend base url if it is relative url
        m3u8_link = _full_link(_link)
        m3u8_links.append({
            'resolution': _res.replace('p',''),
            'resolution_size': _pixels,
            'downloadLink': m3u8_link,
        })
    return m3u8_links

def unpad(s): return s[:-ord(s[len(s)-1:])]

def aes_decrypt(word: str, key: bytes, iv: bytes):
    # Decode the base64-encoded message
    encrypted_msg = base64.b64decode(word)
    # set up the AES cipher in CBC mode
    cipher = AES.new(key, AES.MODE_CBC, iv)
    # Decrypt the message and remove the PKCS#7 padding
    decrypted_msg = unpad(cipher.decrypt(encrypted_msg))
    # get the decrypted message using UTF-8 encoding
    decrypted_msg = decrypted_msg.decode('utf-8').strip()
    return decrypted_msg

def pad(s): return s + (16 - len(s) % 16) * chr(16 - len(s) % 16)

def aes_encrypt(word: str, key: bytes, iv: bytes):
    # Encrypt the message and add PKCS#7 padding
    padded_message = pad(word)
    # set up the AES cipher in CBC mode
    cipher = AES.new(key, AES.MODE_CBC, iv)
    encrypted_message = cipher.encrypt(padded_message.encode('utf-8'))
    # Base64-encode the encrypted message
    base64_encrypted_message = base64.b64encode(encrypted_message).decode('utf-8')
    return base64_encrypted_message

async def get_download_sources(**gdl_config):
    '''
    extract download link sources
    '''
    # unpack configuration dictionary
    link = gdl_config['link']
    encrypted_url_args_regex = gdl_config['encrypted_url_args_regex']
    download_fetch_link = gdl_config['download_fetch_link']

    # extract encryption, decryption keys and iv
    stream_page_content = await req(link, return_type='bytes')

    # get encryption, decryption keys and iv
    if 'crypt_keys_regex' in gdl_config:
        crypt_keys_regex = gdl_config['crypt_keys_regex']
        try:
            encryption_key, iv, decryption_key = (
                _.group(1) for _ in crypt_keys_regex.finditer(stream_page_content)
            )

        except Exception as e:
            return {'error': f'Failed to extract encryption keys. Error: {e}'}

    else:
        encryption_key = gdl_config['encryption_key']
        decryption_key = gdl_config['decryption_key']
        iv = gdl_config['iv']

    # get encrypted url arguments and decrypt
    try:
        encrypted_args = encrypted_url_args_regex.search(stream_page_content).group(1)
        if encrypted_args is None or encrypted_args == '':
            raise Exception('Encrypted url arguments not found in stream link')

        decrypted_args = aes_decrypt(encrypted_args, encryption_key, iv)
        if decrypted_args is None or decrypted_args == '':
            raise Exception('Failed to decrypt extracted url arguments')

    except Exception as e:
        return {'error': f'Failed to fetch download url arguments. Error: {e}'}

    # extract url params & get id value
    try:
        uid = parse_qs(urlparse(link).query).get('id')[0]
        if uid is None or uid == '':
            raise Exception('ID not found in stream link')
    except Exception as e:
        return {'error': f'Failed to fetch Stream ID with error: {e}'}

    # encrypt the uid and construct download link with required parameters
    encrypted_uid = aes_encrypt(uid, encryption_key, iv)
    stream_base_url = '/'.join(link.split('/')[:3])
    dl_sources_link = f'{stream_base_url}/{download_fetch_link}?id={encrypted_uid}&alias={decrypted_args}'

    try:
        # get encrpyted response with download links
        encrypted_response = await req(dl_sources_link, return_type='text')
        encrypted_response = json.loads(encrypted_response)['data']

        # decode the response
        decoded_response = aes_decrypt(encrypted_response, decryption_key, iv)
        decoded_response = json.loads(decoded_response)

    except Exception as e:
        return {'error': f'Invalid response received. Error: {e}'}

    # extract & flatten all download links (including source & backup) from decoded response
    download_links = []
    for key in ['source', 'source_bk']:
        if decoded_response.get(key, '') != '':
            download_links.extend(decoded_response.get(key))

    if len(download_links) == 0:
        return {'error': 'No download links found'}

    return download_links

async def get_stream_link(link, stream_links_element):
    '''
    return stream link for extracting download links
    '''
    pad_https = lambda x: 'https:' + x if x.startswith('/') else x
    res = await req(link)
    soup = BS(res, "html.parser")
    for stream in soup.select(stream_links_element):
        if 'iframe' in stream_links_element:
            stream_link = stream['src']
            return pad_https(stream_link)
        elif 'active' in stream.get('class'):
            stream_link = stream['data-video']
            return pad_https(stream_link)

def get_episodes_list(soup: BS):
    '''Extract episodes and return as a list'''
    episode_list = []

    sub_types = soup.select("ul.items li a div.type span")
    upload_times = soup.select("ul.items li a span.date")
    links = soup.select("ul.items li a")

    # get episode links
    for sub_typ, upload_time, link in zip(sub_types, upload_times, links):
        ep_link = link['href']
        if ep_link.startswith('/'):
            ep_link = BASE_URL + ep_link
        ep_name = link.select_one('div.name').text.strip()
        ep_no = ep_name.split()[-1]
        ep_no = float(ep_no) if '.' in ep_no else int(ep_no)
        ep_upload_time = upload_time.text.strip()
        ep_sub_typ = sub_typ.text.strip().capitalize()
        episode_list.append({
            'episode': ep_no,
            'episodeName': ep_name,
            'episodeLink': ep_link,
            'episodeSubs': ep_sub_typ,
            'episodeUploadTime': ep_upload_time
        })

    return episode_list

async def req(url, return_type: str='text'):
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            if response.status == 200:
                if return_type=='text': return await response.text()
                elif return_type=='bytes': return await response.read()

asyncio.run(main())