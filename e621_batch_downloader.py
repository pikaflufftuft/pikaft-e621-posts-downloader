# https://github.com/pikaflufftuft/pikaft-e621-posts-downloader

import os
import json
import argparse
from bs4 import BeautifulSoup
import requests
from tqdm.auto import tqdm
import shutil
import gzip
import polars as pl
import subprocess
import cv2
import multiprocessing
from itertools import repeat
from ctypes import c_int
import re

def check_param_batch_count(prms):
    batch_count = None
    for param_name, parameter in prms.items():
        if isinstance(parameter,list):   
            if batch_count is None:
                batch_count = len(parameter)
            else:
                if len(parameter) != batch_count:
                    raise ValueError(f'Batch count inconsistent with {param_name}. Expected {batch_count}, found {len(parameter)} instead')
    
    if isinstance(prms['save_searched_list_type'],list) and not isinstance(prms['save_searched_list_path'],list):
        raise ValueError('there should be no multiple save_searched_list_type for a single save_searched_list_path')
    
    if batch_count is None:
        batch_count = 1
    
    return batch_count

def normalize_params(prms, batch_count):
    for param_name, parameter in prms.items():
        if not isinstance(parameter,list):
            prms[param_name] = [parameter] * batch_count

def check_valid_param(lst, name, options, typ=None):
    for item in lst:
        if options is not None:
            if item not in options:
                raise ValueError(f'{name} of {item} is invalid. Use {options} only.')
        elif not isinstance(item,typ):
            raise ValueError(f'Invalid {name} type of {item}. Use type:{typ} only.')

def removeslash(s): # removesuffix version for python 3.8
    return s[:-1] if (s[-1] == '/') else s

def prep_params(prms, batch_count, base_folder):
    cat_to_num = {'general':0,'artist':1,'rating':2,'copyright':3,'character':4,'species':5,'invalid':6,'meta':7,'lore':8}
    cat_set = set(cat_to_num.keys())

    check_valid_param(prms["batch_folder"], 'batch_folder', None, str)
    for i, folder in enumerate(prms["batch_folder"]):
        if os.path.isabs(folder):
            prms["batch_folder"][i] = removeslash(folder)
        else:
            prms["batch_folder"][i] = removeslash(f'{base_folder}/{folder.strip("/")}')  
        os.makedirs(prms["batch_folder"][i], exist_ok=True)

    check_valid_param(prms["required_tags"], 'required_tags', None, str)
    check_valid_param(prms["blacklist"], 'blacklist', None, str)

    check_valid_param(prms["include_png"], 'include_png', (True, False))
    check_valid_param(prms["include_jpg"], 'include_jpg', (True, False))
    check_valid_param(prms["include_gif"], 'include_gif', (True, False))
    check_valid_param(prms["include_webm"], 'include_webm', (True, False))
    check_valid_param(prms["include_swf"], 'include_swf', (True, False))

    for i, g in enumerate(zip(prms["include_png"], prms["include_jpg"], prms["include_gif"], prms["include_webm"], prms["include_swf"])):
        if not any(g):
            raise ValueError(f'Please include at least one file type at batch {i}')

    check_valid_param(prms["include_explicit"], 'include_explicit', (True, False))
    check_valid_param(prms["include_questionable"], 'include_questionable', (True, False))
    check_valid_param(prms["include_safe"], 'include_safe', (True, False))
    
    for i, g in enumerate(zip(prms["include_explicit"], prms["include_questionable"], prms["include_safe"])):
        if not any(g):
            raise ValueError(f'Please include at least one rating at batch {i}')
    
    check_valid_param(prms["min_score"], 'min_score', None, int)
    check_valid_param(prms["min_fav_count"], 'min_fav_count', None, int)

    check_valid_param(prms["min_date"], 'min_date', None, str)
    for date in prms["min_date"]:
        if re.search("^\d{4}\-(0[1-9]|1[012])\-(0[1-9]|[12][0-9]|3[01])$|^\d{4}\-(0[1-9]|1[012])$|^\d{4}$", date) is None:
            raise ValueError(f'Incorrect date format "{date}" Format should be YYYY-MM-DD or YYYY-MM or YYYY')
    
    check_valid_param(prms["min_area"], 'min_area', None, int)
    for idx in range(batch_count):
        if prms["min_area"][idx] < 0:
            prms["min_area"][idx] = -1
    
    check_valid_param(prms["skip_posts_file"], 'skip_posts_file', None, str)
    for f in prms["skip_posts_file"]:
        if not os.path.isfile(f) and f != '':
            raise RuntimeError(f'skip_posts_file {f} not found')  
    
    check_valid_param(prms["skip_posts_type"], 'skip_posts_type', ('id','md5'))
    check_valid_param(prms["do_sort"], 'do_sort', (True,False))
    check_valid_param(prms["top_n"], 'top_n', None, int)
    for i, n in enumerate(prms["top_n"]):
        if n < 2:
            prms["top_n"][i] = 1
    
    check_valid_param(prms["save_searched_list_type"], 'save_searched_list_type', ('id','md5', 'None'))
    
    check_valid_param(prms["save_searched_list_path"], 'save_searched_list_path', None, str)
    for i, p, t, base in zip(range(batch_count), prms["save_searched_list_path"], prms["save_searched_list_type"], prms["batch_folder"]):
        if t != 'None':
            if p != '':
                dirpath = os.path.dirname(p)
                if os.path.isabs(dirpath):
                    os.makedirs(dirpath, exist_ok=True)
                else:
                    prms["save_searched_list_path"][i] = base + '/' + prms["save_searched_list_path"][i].strip('/')
                    os.makedirs(base + '/' + dirpath.strip('/'), exist_ok=True)
            else:
                prms["save_searched_list_path"][i] = base + f'/list_of_searched_{t}s.txt'
        else:
            prms["save_searched_list_path"][i] = None
    
    get_searched_list_from_path = {}
    get_searched_list_type_from_path = {}
    for i, path in enumerate(prms["save_searched_list_path"]):
        if path is not None:
            if path not in get_searched_list_from_path:
                get_searched_list_from_path[path] = set()
                get_searched_list_type_from_path[path] = prms["save_searched_list_type"][i]
            else:
                if get_searched_list_type_from_path[path] != prms["save_searched_list_type"][i]:
                    raise ValueError(f'Found reassignment of save type for save_searched_list_path {path} in batch {i}')
    prms["get_searched_list_from_path"] = get_searched_list_from_path
    prms["get_searched_list_type_from_path"] = get_searched_list_type_from_path
    
    
    check_valid_param(prms["downloaded_posts_folder"], 'downloaded_posts_folder', None, str)
    for i in range(batch_count):
        prms["downloaded_posts_folder"][i] = prms["downloaded_posts_folder"][i].strip('/') + '/'
        if os.path.isabs(prms["downloaded_posts_folder"][i]):                
            os.makedirs(prms["downloaded_posts_folder"][i], exist_ok=True)
        else:
            prms["downloaded_posts_folder"][i] = prms["batch_folder"][i] + '/' + prms["downloaded_posts_folder"][i]
            os.makedirs(prms["downloaded_posts_folder"][i], exist_ok=True)

    for filetype_folder in ('png_folder', 'jpg_folder', 'gif_folder', 'webm_folder', 'swf_folder'):
        check_valid_param(prms[filetype_folder], filetype_folder, None, str)
        for i in range(batch_count):
            if prms[filetype_folder][i] == '':
                prms[filetype_folder][i] = prms["downloaded_posts_folder"][i]
            else:
                prms[filetype_folder][i] = prms[filetype_folder][i].strip('/') + '/'
                if os.path.isabs(prms[filetype_folder][i]):                
                    os.makedirs(prms[filetype_folder][i], exist_ok=True)
                else:
                    prms[filetype_folder][i] = prms["downloaded_posts_folder"][i] + prms[filetype_folder][i]
                    os.makedirs(prms[filetype_folder][i], exist_ok=True)

    
    check_valid_param(prms["save_filename_type"], 'save_filename_type', ('id', 'md5'))
    check_valid_param(prms["include_tag_file"], 'include_tag_file', (True, False))
    check_valid_param(prms["skip_post_download"], 'skip_post_download', (True, False))
        
    check_valid_param(prms["tag_sep"], 'tag_sep', None, str)
    for i,sep in enumerate(prms["tag_sep"]):
        if sep == '':
            raise ValueError(f'tag separator in batch {i} is empty!')
    
    check_valid_param(prms["include_explicit_tag"], 'include_explicit_tag', (True, False))
    check_valid_param(prms["include_questionable_tag"], 'include_questionable_tag', (True, False))
    check_valid_param(prms["include_safe_tag"], 'include_safe_tag', (True, False))
    check_valid_param(prms["reorder_tags"], 'reorder_tags', (True, False))
    
    check_valid_param(prms["tag_order_format"], 'tag_order_format', None, str)
    tag_order = []
    selected_cats = []
    for form in prms["tag_order_format"]:
        sub_tag_order = [s.strip() for s in form.split(',')]
        sub_tag_order = [s for s in sub_tag_order if s != '']
        if len(sub_tag_order) == 0:
            raise ValueError('Please include at least one category')
        tag_order.append(sub_tag_order)
        sub_selected_cats = []
        for cat in sub_tag_order:
            if cat not in cat_set:
                raise ValueError(f'{cat} is not a tag category')
            sub_selected_cats.append(cat_to_num[cat])
        selected_cats.append(sub_selected_cats)
    prms["tag_order"] = tag_order
    prms["selected_cats"] = selected_cats    
    
    check_valid_param(prms["prepend_tags"], 'prepend_tags', None, str)
    check_valid_param(prms["append_tags"], 'append_tags', None, str)
    check_valid_param(prms["replace_underscores"], 'replace_underscores', (True, False))
    check_valid_param(prms["remove_parentheses"], 'remove_parentheses', (True, False))
    
    check_valid_param(prms["remove_tags_list"], 'remove_tags_list', None, str)
    for f in prms["remove_tags_list"]:
        if f != '':
            if not os.path.isfile(f):
                raise ValueError(f'remove_tags_list {f} file not found')

    check_valid_param(prms["replace_tags_list"], 'replace_tags_list', None, str)
    replace_tags = []
    for f in prms["replace_tags_list"]:
        if f != '':
            if not os.path.isfile(f):
                raise ValueError(f'replace_tags_list {f} file not found')
            with open(f, 'r') as file:
                d = {}
                for line in file:
                    l = line.strip().split(',')
                    key = l[0].strip()
                    val = l[1].strip()
                    if key == '' or val == '':
                        raise ValueError(f'Empty text found in replace_tags_list {f}')
                    d[key] = val
            replace_tags.append(d)
        else:
            replace_tags.append({})
    prms["replace_tags"] = replace_tags


    check_valid_param(prms["tag_count_list_folder"], 'tag_count_list_folder', None, str)
    for i in range(batch_count):
        prms["tag_count_list_folder"][i] = prms["tag_count_list_folder"][i].strip('/') + '/'
        if os.path.isabs(prms["tag_count_list_folder"][i]):                
            os.makedirs(prms["tag_count_list_folder"][i], exist_ok=True)
        else:
            prms["tag_count_list_folder"][i] = prms["batch_folder"][i] + '/' + prms["tag_count_list_folder"][i]
            os.makedirs(prms["tag_count_list_folder"][i], exist_ok=True)
    
    get_all_tag_counter_from_path = {}
    get_cat_tag_counter_from_path = {}
    for batch_num, path in enumerate(prms["tag_count_list_folder"]):
        if path not in get_all_tag_counter_from_path:
            get_all_tag_counter_from_path[path] = {}
            get_cat_tag_counter_from_path[path] = {i:{} for i in range(9)}
    prms["get_all_tag_counter_from_path"] = get_all_tag_counter_from_path
    prms["get_cat_tag_counter_from_path"] = get_cat_tag_counter_from_path

    check_valid_param(prms["min_short_side"], 'min_short_side', None, int)
    for s in prms["min_short_side"]:
        if -1 < s < 320:
            raise ValueError(f'min_short_side of {s} is too short')

    for i,ext in enumerate(prms["img_ext"]):
        if ext not in ('.png', '.jpg', 'png', 'jpg', 'same_as_original'):
            raise ValueError(f"Invalid img_ext value: {ext} Use '.png', '.jpg', 'png', 'jpg', 'same_as_original' only")
        if ext[0] != '.':
            prms["img_ext"][i] = '.' + prms["img_ext"][i]


    check_valid_param(prms["delete_original"], 'delete_original', (True, False))
    check_valid_param(prms["resized_img_folder"], 'resized_img_folder', None, str)
 
    for i in range(batch_count):
        prms["resized_img_folder"][i] = prms["resized_img_folder"][i].strip('/') + '/'
        if os.path.isabs(prms["resized_img_folder"][i]):                
            os.makedirs(prms["resized_img_folder"][i], exist_ok=True)
        else:
            prms["resized_img_folder"][i] = prms["batch_folder"][i] + '/' + prms["resized_img_folder"][i]
            os.makedirs(prms["resized_img_folder"][i], exist_ok=True)

    check_valid_param(prms["method_tag_files"], 'method_tag_files', ('relocate', 'copy'))
        
    for do_sort, min_score, min_date, top_n, i in zip(prms["do_sort"], prms["min_score"], prms["min_date"], prms["top_n"], range(batch_count)):
        if do_sort and (min_score < 300) and (min_date < '2017') and (top_n > 1):
            print(f'## Caution: collecting top {top_n} posts with the set min_score of {min_score} and min_date of {min_date} in batch {i} can take considerable time')

def get_db(base_folder, posts_csv='', tags_csv='', e621_posts_list_filename='', e621_tags_list_filename=''):
    
    db_export_file_path = base_folder + '/db_export.html'
    if not os.path.isfile(db_export_file_path):
        os.system(f'curl https://e621.net/db_export/ -o {db_export_file_path}')
    with open(db_export_file_path) as f:
        gfg = BeautifulSoup(''.join(f.readlines()), features='html.parser')
    gfg_lines = gfg.get_text().split('\n')
    
    if e621_posts_list_filename == '':
        e621_posts_list_filename = f'{base_folder}/e621_posts_list.parquet'
    if not os.path.isfile(e621_posts_list_filename):
        found_first = None
        for line in gfg_lines:
            if 'posts' in line:
                found_first = True
                posts_filename = line.split(' ')[0]
            elif found_first:
                break
        if posts_csv == '':
            posts_csv = f'{base_folder}/{posts_filename[:-3]}'
        if not os.path.isfile(posts_csv):
            posts_link = 'https://e621.net/db_export/' + posts_filename
            posts_file_path = f'{base_folder}/{posts_filename}'
            print(posts_file_path)
            if not os.path.isfile(posts_file_path):
                with requests.get(posts_link, stream=True) as r:
                    total_length = int(r.headers.get("Content-Length"))
                    with tqdm.wrapattr(r.raw, "read", total=total_length, desc="") as raw:
                        with open(posts_file_path, 'wb') as output:
                            shutil.copyfileobj(raw, output)
            
            print('## Unpacking',posts_file_path,'...')
            with gzip.open(posts_file_path, 'rb') as f_in:
                with open(posts_csv, 'wb') as f_out:
                    shutil.copyfileobj(f_in, f_out)
        
        e621_posts_list_filename = f'{base_folder}/e621_posts_list.parquet'
        print('## Optimizing posts list data, this will take a few minutes')
        pl.scan_csv(posts_csv).select(['id', 'created_at', 'md5', 'rating', 'image_width', 'image_height', 'tag_string', 'fav_count', 'file_ext', 'is_deleted', 'score']).filter(pl.col('is_deleted') == 'f').collect().write_parquet(e621_posts_list_filename)
    
    if e621_tags_list_filename == '':
        e621_tags_list_filename = f'{base_folder}/e621_tags_list.parquet'
    if not os.path.isfile(e621_tags_list_filename):
        found_first = None
        for line in gfg_lines:
            if 'tags' in line:
                found_first = True
                tags_filename = line.split(' ')[0]
            elif found_first:
                break
        if tags_csv == '':
            tags_csv = f'{base_folder}/{tags_filename[:-3]}'
        if not os.path.isfile(tags_csv):
            tags_link = 'https://e621.net/db_export/' + tags_filename
            tags_file_path = f'{base_folder}/{tags_filename}'
            print(tags_file_path)
            if not os.path.isfile(tags_file_path):
                with requests.get(tags_link, stream=True) as r:
                    total_length = int(r.headers.get("Content-Length"))
                    with tqdm.wrapattr(r.raw, "read", total=total_length, desc="") as raw:
                        with open(tags_file_path, 'wb') as output:
                            shutil.copyfileobj(raw, output)
            
            print('## Unpacking',tags_file_path,'...')
            with gzip.open(tags_file_path, 'rb') as f_in:
                with open(tags_csv, 'wb') as f_out:
                    shutil.copyfileobj(f_in, f_out)
        
        e621_tags_list_filename = f'{base_folder}/e621_tags_list.parquet'
        print('## Optimizing tags list data, this will take a few seconds')
        pl.scan_csv(tags_csv).select(['name','category','post_count']).collect().write_parquet(e621_tags_list_filename)

    tags_save_path = base_folder + '/tags/'
    
    os.makedirs(tags_save_path, exist_ok=True)
    
    category_labels = {0: "general", 1: "artist", 3: "copyright", 4: "character", 5: "species", 6: "invalid", 7: "meta", 8: "lore"}
    
    min_post_count = 1
    
    df = pl.scan_parquet(e621_tags_list_filename)
    
    df = df.filter(pl.col('post_count') >= min_post_count)
    if not os.path.exists(f"{tags_save_path}tags.parquet"):
        df.collect().write_parquet(f"{tags_save_path}tags.parquet")
        print(f"## {tags_save_path}tags.parquet saved")
    
    for category in category_labels.keys():
        if not os.path.exists(f"{tags_save_path + category_labels[category]}.parquet"):
            newdf = df.filter(pl.col('category') == category)
            newdf = newdf.drop(columns=['category'])
            newdf.collect().write_parquet(f"{tags_save_path + category_labels[category]}.parquet")
            print(f"## {tags_save_path + category_labels[category]}.parquet saved")

    rating_d = {
        'name':['explicit', 'questionable', 'safe'],
        'category':[2, 2, 2]
    }
    
    df = pl.read_parquet(f"{tags_save_path}tags.parquet", columns=['name', 'category'])

    rdf = pl.DataFrame(rating_d)
    df = pl.concat([df,rdf])
    
    tag_to_cat = dict(zip(df["name"], df["category"]))
    del df

    return e621_posts_list_filename, tag_to_cat

def collect_posts(prms, batch_num, e621_posts_list_filename):
    
    print(f"## Collecting posts for batch {batch_num}")
    df = pl.read_parquet(e621_posts_list_filename)

    if not prms["include_explicit"][batch_num]:
        df = df.filter(pl.col('rating') != 'e')
    if not prms["include_questionable"][batch_num]:
        df = df.filter(pl.col('rating') != 'q')
    if not prms["include_safe"][batch_num]:
        df = df.filter(pl.col('rating') != 's')
    
    print(f'## Removing posts with score < {prms["min_score"][batch_num]}')
    df = df.filter(pl.col('score') >= prms["min_score"][batch_num])
    
    print(f'## Removing posts with favorite count < {prms["min_fav_count"][batch_num]}')
    df = df.filter(pl.col('fav_count') >= prms["min_fav_count"][batch_num])
    
    included_file_ext = set(['png'*prms["include_png"][batch_num], 'jpg'*prms["include_jpg"][batch_num], 'gif'*prms["include_gif"][batch_num], 'webm'*prms["include_webm"][batch_num], 'swf'*prms["include_swf"][batch_num]])
    if '' in included_file_ext:
        included_file_ext.remove('')
    included_file_ext = '|'.join(included_file_ext)
    if included_file_ext:
        df = df.filter(pl.col('file_ext').str.contains(included_file_ext))
    
    if prms["min_date"][batch_num] >= '2007':
        print(f'## Removing posts before date {prms["min_date"][batch_num]}')
        df = df.filter(pl.col("created_at") >= prms["min_date"][batch_num])
        df = df.drop(columns=['created_at'])
    
    if prms["skip_posts_file"][batch_num]:
        print(f'## skipping listed posts in {prms["skip_posts_file"][batch_num]}')
        with open(prms["skip_posts_file"][batch_num], 'r') as f:
            skip_posts = list(set([s.strip() for s in f]))
        df = df.filter(~pl.col(prms["skip_posts_type"][batch_num]).is_in(skip_posts))
    
    if prms["min_area"][batch_num] >= 65536:
        print(f'## Removing posts with dimension area less than {prms["min_area"][batch_num]}px')
        df = df.filter(pl.col("image_width") * pl.col("image_height") >= prms["min_area"][batch_num])
        df = df.drop(columns=['image_width','image_height'])
    
    print("## Getting posts that has all required tags")
    all_required_tags = []
    tag_groups = set([s.strip().lower() for s in prms["required_tags"][batch_num].split('|')])
    if '' in tag_groups:
        tag_groups.remove('')
    expr = None
    for group in tag_groups:
        tags = set([s.strip() for s in group.split(',')])
        if '' in tags:
            tags.remove('')
        all_required_tags.append(tags)
        escaped_tags = [re.escape(word).replace(r'\*', r'\S*') for word in tags]
        sub_expr = None
        for tag in escaped_tags:
            pattern = r'(^|\s)(' + tag + r')($|\s)'
            if sub_expr is None:
                sub_expr = pl.col('tag_string').str.contains(pattern)
            else:
                sub_expr &= pl.col('tag_string').str.contains(pattern)
        if expr is None:
            expr = sub_expr
        else:
            expr |= sub_expr
    if expr is not None:
        df = df.filter(expr)
    
    print('## Removing posts that has blacklisted tags')
    tag_groups = set([s.strip().lower() for s in prms["blacklist"][batch_num].split('|')])
    if '' in tag_groups:
        tag_groups.remove('')

    for group in tag_groups:
        tags = set([s.strip() for s in group.split(',')])
        if '' in tags:
            tags.remove('')
        if not any([tags <= subset for subset in all_required_tags]):
            escaped_tags = [re.escape(word).replace(r'\*', r'\S*') for word in tags]
            sub_expr = None
            for tag in escaped_tags:
                pattern = r'(^|\s)(' + tag + r')($|\s)'
                if sub_expr is None:
                    sub_expr = pl.col('tag_string').str.contains(pattern)
                else:
                    sub_expr &= pl.col('tag_string').str.contains(pattern)
            if sub_expr is not None:
                df = df.filter(~sub_expr)

    
    if prms["top_n"][batch_num] > 1:
        print(f'## Getting top {prms["top_n"][batch_num]} posts')
        if prms["do_sort"][batch_num]:
            top_n = prms["top_n"][batch_num]
            df = df.filter(pl.col('score') >= pl.col('score').top_k(top_n).last()).sort('score', reverse=True).head(top_n)
        else:
            df = df.head(n=prms["top_n"][batch_num])

    posts_save_path = f'{prms["batch_folder"][batch_num]}/filtered_posts_{batch_num}.parquet'
    print(f'## Saving filtered e621 posts list for batch {batch_num} in {posts_save_path}')
    df.write_parquet(posts_save_path)

    if prms["save_searched_list_type"][batch_num] != 'None':
        prms["get_searched_list_from_path"][prms["save_searched_list_path"][batch_num]].update(
            df[prms["save_searched_list_type"][batch_num]].to_list()
            )

    return posts_save_path

def create_searched_list(prms):
    for path in prms["save_searched_list_path"]:
        if path is not None:
            l = prms["get_searched_list_from_path"][path]
            save_list_type = prms["get_searched_list_type_from_path"][path]
            print(f"## Saving a list of {save_list_type}s from the collected posts")
            with open(path, 'w') as f:
                f.write('\n'.join([str(s) for s in l]))

def download_posts(prms, batch_nums, posts_save_paths, tag_to_cat, base_folder='', batch_mode=False):

    img_lists = []
    __df = pl.DataFrame()
    for batch_num, posts_save_path in zip(batch_nums, posts_save_paths):
        df = pl.read_parquet(posts_save_path)
        
        length = df.shape[0]
        
        if prms["remove_tags_list"][batch_num] != '':
            with open(prms["remove_tags_list"][batch_num], 'r') as f:
                remove_tags = set([s.strip() for s in f])
                if '' in remove_tags:
                    remove_tags.remove('')
        else:
            remove_tags = set()
    
        replace_tags = prms["replace_tags"][batch_num]
    
        ext_directory = {'png':prms["png_folder"][batch_num], 'jpg':prms["jpg_folder"][batch_num], 'webm':prms["webm_folder"][batch_num], 'gif':prms["gif_folder"][batch_num]}
        
        base = pl.repeat('https://static1.e621.net/data/', n=length, eager=True)
        slash = pl.repeat('/', n=length, eager=True)
        dot = pl.repeat('.', n=length, eager=True)
        df = df.with_columns((base + df['md5'].str.slice(0,length=2) + slash + df['md5'].str.slice(2,length=2) + slash + df['md5'] + dot + df['file_ext']).alias("download_links"))
        
        # use dict_map in new version
        df = df.join(pl.DataFrame({'directory': ext_directory.values(), 'key': ext_directory.keys()}), left_on='file_ext', right_on='key', how='left')
        
        df = df.with_columns((pl.repeat(' dir=', n=length, eager=True) + df['directory']).alias("cmd_directory"))
    
        df = df.with_columns(df[prms["save_filename_type"][batch_num]].cast(str))
        df = df.with_columns((df[prms["save_filename_type"][batch_num]] + dot + df['file_ext']).alias("filename"))
        df = df.with_columns((pl.repeat(' out=', n=length, eager=True) + df['filename']).alias("cmd_filename"))
        df = df.with_columns((df[prms["save_filename_type"][batch_num]] + pl.repeat('.txt', n=length, eager=True)).alias("tagfilebasename"))
        df = df.with_columns((df['directory'] + df['tagfilebasename']).alias("tagfilename"))
        
        img_df = df.select(['directory','filename','tagfilebasename','file_ext']).filter(pl.col('file_ext').str.contains('png|jpg'))
    
        img_lists.append([img_df['directory'].to_list(), img_df['filename'].to_list(), img_df['tagfilebasename'].to_list()])
        
        
        if not prms["skip_post_download"][batch_num] and not batch_mode:
            df.select(['download_links','cmd_directory','cmd_filename']).write_csv(prms["batch_folder"][batch_num] + '/__.txt', sep='\n', has_header=False)
            print('## Downloading posts')
            has_error = False
            try:
                stdout = subprocess.check_output(['aria2c','-c','-x','16','-k','1M','-i',prms["batch_folder"][batch_num] + '/__.txt'])
            except subprocess.CalledProcessError as e:
                print('## Some unavailable posts found (you can ignore this)')
                with open(prms["batch_folder"][batch_num] + f'/download_error_log_{batch_num}.txt', 'w') as f:
                    f.write(e.output.decode('utf-8'))
                has_error = True
            if not has_error:
                with open(prms["batch_folder"][batch_num] + f'/download_log_{batch_num}.txt', 'w') as f:
                    f.write(stdout.decode('utf-8'))
                print('## Posts downloaded')
            else:
                print('## Finished downloading, however some were not downloaded (most likely posts that have generally prms["blacklist"][batch_num]ed tags)')
            os.remove(prms["batch_folder"][batch_num] + '/__.txt')
        elif not prms["skip_post_download"][batch_num]:
            __df = __df.vstack(df.select(['download_links','cmd_directory','cmd_filename']))
        
        df = df.drop(['download_links','directory','cmd_directory','file_ext','filename','cmd_filename','tagfilebasename'])
        rating_tags = {}
        if prms["include_explicit_tag"][batch_num]:
            rating_tags['e'] = 'explicit'
        if prms["include_questionable_tag"][batch_num]:
            rating_tags['q'] = 'questionable'
        if prms["include_safe_tag"][batch_num]:
            rating_tags['s'] = 'safe'
    
        path = prms["tag_count_list_folder"][batch_num]
        all_tag_count = prms["get_all_tag_counter_from_path"][path]
        category_ctr = prms["get_cat_tag_counter_from_path"][path]
        selected_cats = prms["selected_cats"][batch_num]
        reorder_tags = prms["reorder_tags"][batch_num]
        tag_sep = prms["tag_sep"][batch_num]
        prepend_tags = [s.strip() for s in prms["prepend_tags"][batch_num].split(tag_sep)]
        prepend_tags = [s for s in prepend_tags if s != '']
        append_tags = [s.strip() for s in prms["append_tags"][batch_num].split(tag_sep)]
        append_tags = [s for s in append_tags if s != '']
        replace_underscores = prms["replace_underscores"][batch_num]
        remove_parentheses = prms["remove_parentheses"][batch_num]
        if prms["include_tag_file"][batch_num]:
            for idx in range(length):
                rating = df['rating'][idx]
                if rating in rating_tags:
                    tags = [rating_tags[rating]] + df['tag_string'][idx].split(' ')
                else:
                    tags = df['tag_string'][idx].split(' ')
                segregate = {}
                unsegregated = []
                for tag in tags:
                    if tag not in remove_tags:
                        if tag in tag_to_cat:
                            category_num = tag_to_cat[tag]
                            if tag in replace_tags:
                                tag = replace_tags[tag]
                            if category_num in selected_cats:
                                if reorder_tags:
                                    if category_num in segregate:
                                        segregate[category_num].append(tag)
                                    else:
                                        segregate[category_num] = [tag]
                                else:
                                    unsegregated.append(tag)
                                if path:
                                    if tag in all_tag_count:
                                        all_tag_count[tag] += 1
                                    else:
                                        all_tag_count[tag] = 1
                                    if tag in category_ctr[category_num]:
                                        category_ctr[category_num][tag] += 1
                                    else:
                                        category_ctr[category_num][tag] = 1
    
                if reorder_tags:
                    category_nums = [c for c in selected_cats if c in segregate]
                    updated_tags = []
                    for cat_num in category_nums:
                        updated_tags += segregate[cat_num]
                else:
                    updated_tags = unsegregated
                if prepend_tags:
                    updated_tags = [tag for tag in prepend_tags if not (tag in updated_tags)] + updated_tags
                if append_tags:
                    updated_tags = updated_tags + [tag for tag in append_tags if not (tag in updated_tags)]
                updated_tags = tag_sep.join(updated_tags)
                if replace_underscores:
                    updated_tags = updated_tags.replace('_',' ')
                if remove_parentheses:
                    updated_tags = updated_tags.replace('(','')
                    updated_tags = updated_tags.replace(')','')
    
                with open(df['tagfilename'][idx], 'w') as f:
                    f.write(updated_tags)
                
            if path:
                if prepend_tags:
                    for tag in prepend_tags:
                        if tag in all_tag_count:
                            all_tag_count[tag] += length
                        else:
                            all_tag_count[tag] = length
                if append_tags:
                    for tag in append_tags:
                        if tag in all_tag_count:
                            all_tag_count[tag] += length
                        else:
                            all_tag_count[tag] = length
    
    if batch_mode:
        __df.write_csv(base_folder + '/__.txt', sep='\n', has_header=False)
        print('## Downloading posts')
        has_error = False
        try:
            stdout = subprocess.check_output(['aria2c','-c','-x','16','-k','1M','-i',base_folder + '/__.txt'])
        except subprocess.CalledProcessError as e:
            print('## Some unavailable posts found (you can ignore this)')
            with open(prms["batch_folder"][batch_num] + f'/download_error_log_{batch_num}.txt', 'w') as f:
                f.write(e.output.decode('utf-8'))
            has_error = True
        if not has_error:
            with open(base_folder + '/download_log.txt', 'w') as f:
                f.write(stdout.decode('utf-8'))
            print('## Posts downloaded')
        else:
            print('## Finished downloading, however some were not downloaded (most likely posts that have generally prms["blacklist"][batch_num]ed tags)')
        os.remove(base_folder + '/__.txt')
    
    return img_lists

def create_tag_count(prms):
    for path in set(prms["tag_count_list_folder"]):
        if path:
            all_tag_count = prms["get_all_tag_counter_from_path"][path]
            category_ctr = prms["get_cat_tag_counter_from_path"][path]
            categories = set([item for sublist in prms["tag_order"] for item in sublist])
            cat_to_num = {'general':0,'artist':1,'rating':2,'copyright':3,'character':4,'species':5,'invalid':6,'meta':7,'lore':8}
            for category in categories:                
                cat_df = pl.DataFrame(list(category_ctr[cat_to_num[category]].items()), schema=[category,'count'])
                cat_df = cat_df.sort(by=['count',category], reverse=[True, False])  
                cat_df.write_csv(path + category + '.csv', has_header=True)
            all_tags_df = pl.DataFrame(list(all_tag_count.items()), schema=['tag','count'])
            all_tags_df = all_tags_df.sort(by=['count','tag'], reverse=[True, False])
            all_tags_df.write_csv(path + 'tags.csv', has_header=True)
            print(f'## Tag count CSVs {path} done!')

def init_counter():
    global counter, counter_lock
    counter = multiprocessing.Value(c_int)
    counter_lock = multiprocessing.Lock()

def increment(length):
    global counter, counter_lock
    with counter_lock:
        counter.value += 1
        print(f'\r## Resizing Images: {counter.value}/{length} ',end='')

def parallel_resize(imgs_folder, img_file, img_ext, min_short_side, num_images, failed_images, delete_original, resized_img_folder):
    resized_img_folder = imgs_folder if (delete_original or resized_img_folder == '') else resized_img_folder
    if (img_ext == 'same_as_original') or (os.path.splitext(img_file)[1] == img_ext):
        resized_filename = resized_img_folder + img_file
    else:
        resized_filename = resized_img_folder + os.path.splitext(img_file)[0] + img_ext

    if resized_img_folder != imgs_folder and os.path.isfile(resized_filename):
        print(f"## {resized_filename} already exists.")
        increment(num_images)
        return

    try:
        image = cv2.imread(imgs_folder + img_file, cv2.IMREAD_COLOR)
        height, width = image.shape[:2]
    except Exception:
        failed_images.append(imgs_folder + img_file)
        increment(num_images)
        return

    img_short_side = min(width, height)
    resized = False
    if (img_short_side > min_short_side) and (min_short_side > 1):
        if width == img_short_side:
            new_width = min_short_side
            new_height = int(height * min_short_side / width)
        else:
            new_width = int(width * min_short_side / height)
            new_height = min_short_side
        image = cv2.resize(image, (new_width, new_height), interpolation = cv2.INTER_AREA)
        resized = True

    if delete_original:
        if os.path.isfile(resized_filename) and resized: # same ext -> overwrite
            cv2.imwrite(resized_filename, image)
        elif resized: # different ext -> delete
            os.remove(imgs_folder + img_file)
            cv2.imwrite(resized_filename, image)
    else:
        if resized_img_folder != imgs_folder: # different folder
            cv2.imwrite(resized_filename, image)
        else: # same folder -> rename original image
            os.rename(imgs_folder + img_file, imgs_folder + '_' + img_file)
            cv2.imwrite(resized_filename, image)
    increment(num_images)


def resize_imgs(prms, batch_num, num_cpu, img_folders, img_files, tag_files):    
    global failed_images
    min_short_side = prms["min_short_side"][batch_num]
    img_ext = prms["img_ext"][batch_num]
    delete_original = prms["delete_original"][batch_num]
    resized_img_folder = prms["resized_img_folder"][batch_num]
    method = prms["method_tag_files"][batch_num]
    
    init_counter()
    
    if img_files:
        print(f'## Resizing Images for batch {batch_num} ...')
    multiprocessing.freeze_support()
    with multiprocessing.Pool(num_cpu) as pool:
        pool.starmap(parallel_resize, zip(img_folders, img_files, repeat(img_ext), repeat(min_short_side), repeat(len(img_files)), repeat(failed_images), repeat(delete_original), repeat(resized_img_folder)))
    print('')
    
    if method == 'relocate':
        print('## Relocating tag files')
    else:
        print('## Copying tag files')
    for img_folder, tag_file in zip(img_folders, tag_files):
        if (not delete_original) and (resized_img_folder != img_folder):
            if method == 'relocate':
                os.rename(img_folder + tag_file, resized_img_folder + tag_file)
            else: # copy
                shutil.copyfile(img_folder + tag_file, resized_img_folder + tag_file)

def resize_imgs_batch(num_cpu, img_folders, img_files, resized_img_folders, min_short_side, img_ext, delete_original, resized_img_folder_batches, delete_original_batches, img_folder_batches, tag_file_batches, method_tag_files):
    global failed_images
    
    init_counter()
    
    if img_files:
        print('## Resizing Images ...')
    multiprocessing.freeze_support()
    with multiprocessing.Pool(num_cpu) as pool:
        pool.starmap(parallel_resize, zip(img_folders, img_files, img_ext, min_short_side, repeat(len(img_files)), repeat(failed_images), delete_original, resized_img_folders))
    print('')

    for i, res_img_fol_batch, del_org_batch, img_fol_batch, tag_file_batch, method in zip(range(len(resized_img_folder_batches)), resized_img_folder_batches, delete_original_batches, img_folder_batches, tag_file_batches, method_tag_files):
        if method == 'relocate':
            print(f'## Relocating tag files. Batch {i}')
        else:
            print(f'## Copying tag files. Batch {i}')
        for img_folder, tag_file in zip(img_fol_batch, tag_file_batch):
            if (not del_org_batch) and (res_img_fol_batch != img_folder):
                if method == 'relocate':
                    os.rename(img_folder + tag_file, res_img_fol_batch + tag_file)
                else: # copy
                    shutil.copyfile(img_folder + tag_file, res_img_fol_batch + tag_file)

def main():
    global failed_images
    print('##################### e621 posts downloader #####################')
    parser = argparse.ArgumentParser(description='e621 posts downloader')
    parser.add_argument('-f', '--basefolder', action='store', type=str, help='default output directory used for storing e621 db files and downloading posts', default='')
    parser.add_argument('-s', '--settings', action='store', type=str, help='path to custom download settings json', required=True)
    parser.add_argument('-c', '--numcpu', type=int, help='number of cpu to use for image resizing, set to -1 for max', default=-1)
    parser.add_argument('-ppb', '--phaseperbatch', action='store_true', help='performing all phases per batch as opposed to completing all batches per phase, e.g., if passed, complete all phases for the current batch before proceeding to the next batch, else, complete posts collection phase before downloading')
    parser.add_argument('-pcsv', '--postscsv', action='store', type=str, help='path to e621 posts csv', default='')
    parser.add_argument('-tcsv', '--tagscsv', action='store', type=str, help='path to e621 tags csv', default='')
    parser.add_argument('-ppar', '--postsparquet', action='store', type=str, help='path to e621 posts parquet', default='')
    parser.add_argument('-tpar', '--tagsparquet', action='store', type=str, help='path to e621 tags parquet', default='')
    args = parser.parse_args()

    base_folder = os.path.dirname(os.path.abspath(__file__))
    if args.basefolder != '':
        base_folder = args.basefolder        
        base_folder = removeslash(base_folder)
        os.makedirs(base_folder, exist_ok=True)

    with open(args.settings, 'r') as json_file:
        prms = json.load(json_file)

    if shutil.which('aria2c') is None:
        raise RuntimeError('aria2c is not installed. Install https://github.com/aria2/aria2/releases/')
    
    if args.postscsv != '':
        if not args.postscsv.endswith('.csv'):
            raise ValueError('Invalid postscsv file type.')
        if not os.path.isfile(args.postscsv):
            raise ValueError(args.postscsv,'not found.')
    if args.tagscsv != '':
        if not args.tagscsv.endswith('.csv'):
            raise ValueError('Invalid tagscsv file type.')
        if not os.path.isfile(args.tagscsv):
            raise ValueError(args.tagscsv,'not found.')
    if args.postsparquet != '':
        if not args.postsparquet.endswith('.parquet'):
            raise ValueError('Invalid postsparquet file type.')
        if not os.path.isfile(args.postsparquet):
            raise ValueError(args.postsparquet,'not found.')
    if args.tagsparquet != '':
        if not args.tagsparquet.endswith('.parquet'):
            raise ValueError('Invalid tagsparquet file type.')
        if not os.path.isfile(args.tagsparquet):
            raise ValueError(args.tagsparquet,'not found.')
    
    max_cpu = multiprocessing.cpu_count()
    num_cpu = max_cpu if (args.numcpu > max_cpu) or (args.numcpu < 1) else args.numcpu
    
    
    print('## Checking number of batches validity')
    batch_count = check_param_batch_count(prms)
    
    normalize_params(prms, batch_count)
    
    print('## Checking setting validity')
    prep_params(prms, batch_count, base_folder)
    
    print('## Checking required files')
    e621_posts_list_filename, tag_to_cat = get_db(base_folder, args.postscsv, args.tagscsv, args.postsparquet, args.tagsparquet)
    
    manager = multiprocessing.Manager()
    failed_images = manager.list()
    
    if args.phaseperbatch:
        for batch_num in range(batch_count):
            print(f"#### Batch {batch_num} ####")
            posts_save_path = collect_posts(prms, batch_num, e621_posts_list_filename)
            image_list = download_posts(prms, [batch_num], [posts_save_path], tag_to_cat)[0]
            if not prms["skip_resize"][batch_num]:
                resize_imgs(prms, batch_num, num_cpu, image_list[0], image_list[1], image_list[2])
        create_searched_list(prms)
        create_tag_count(prms)
    else:
        posts_save_paths = [collect_posts(prms, batch_num, e621_posts_list_filename) for batch_num in range(batch_count)]
        create_searched_list(prms)
        list_of_image_lists = download_posts(prms, list(range(batch_count)), posts_save_paths, tag_to_cat, base_folder, batch_mode=True)
        create_tag_count(prms)
        img_folders = []
        img_files = []
        img_folder_batches = []
        tag_file_batches = []
        resized_img_folder = []
        min_short_side = []
        img_ext = []
        delete_original = []
        for batch_num, image_lists in enumerate(list_of_image_lists):
            if not prms["skip_resize"][batch_num]:
                img_folders += image_lists[0]
                img_files += image_lists[1]
                img_folder_batches.append(image_lists[0])
                tag_file_batches.append(image_lists[2])
                resized_img_folder += [prms["resized_img_folder"][batch_num]]*len(image_lists[0])
                min_short_side += [prms["min_short_side"][batch_num]]*len(image_lists[0])
                img_ext += [prms["img_ext"][batch_num]]*len(image_lists[0])
                delete_original += [prms["delete_original"][batch_num]]*len(image_lists[0])
        resize_imgs_batch(num_cpu, img_folders, img_files, resized_img_folder, min_short_side, img_ext, delete_original, prms["resized_img_folder"], prms["delete_original"], img_folder_batches, tag_file_batches, prms["method_tag_files"])

    if failed_images:
        print(f'## Failed to resize {len(failed_images)} images')
        with open(f'{base_folder}/failed_images.txt', 'w') as f:
            f.write('\n'.join(failed_images))

    print('## Done!')
    print('#################################################################')
    
if __name__ == "__main__":
    main()