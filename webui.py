import gradio as gr
import os
import json
import copy
import multiprocessing as mp
import subprocess as sub

'''
##################################################################################################################################
###################################################     HELPER FUNCTIONS     #####################################################
##################################################################################################################################
'''

def verbose_print(text):
    print(f"{text}")

def load_session_config(f_name):
    session_config = None
    file_exists = os.path.exists(f_name)
    if not file_exists: # create the file
        with open(f_name, 'w') as f:
            f.close()
    else: # load the file
        data_flag = True # detects if the file is empty
        with open(f_name, 'r') as json_file:
            lines = json_file.readlines()
            if len(lines) == 0 or len(lines[0].replace(' ', '')) == 0:
                data_flag = False
            json_file.close()

        if data_flag: # data present
            with open(f_name) as json_file:
                data = json.load(json_file)

                temp_config = [dictionary for dictionary in data]
                if len(temp_config) > 0:
                    session_config = data
                else:
                    session_config = {}
                json_file.close()
    return session_config

def grab_pre_selected(settings, all_checkboxes):
    pre_selected_checkboxes = []
    for key in all_checkboxes:
        if settings[key]:
            pre_selected_checkboxes.append(key)
    return pre_selected_checkboxes

def update_JSON(settings, config_name):
    temp = copy.deepcopy(settings)
    for entry in temp:
        verbose_print(f"{entry}:\t{settings[entry]}")

    with open(config_name, "w") as f:
        json.dump(temp, indent=4, fp=f)
    f.close()
    verbose_print("="*42)

def create_dirs(arb_path):
    if not os.path.exists(arb_path):
        os.makedirs(arb_path)

def execute(cmd):
    popen = sub.Popen(cmd, stdout=sub.PIPE, universal_newlines=True)
    for stdout_line in iter(popen.stdout.readline, ""):
        yield stdout_line
    popen.stdout.close()
    return_code = popen.wait()
    if return_code:
        raise sub.CalledProcessError(return_code, cmd)

def get_list(arb_string, delimeter):
    return arb_string.split(delimeter)

def get_string(arb_list, delimeter):
    return delimeter.join(arb_list)

def from_padded(line):
    if len(line) > 1:# check for padded-0
        if int(line[0]) == 0:# remove the 0, cast to int, return
            return int(line[-1])
    return int(line)

def to_padded(num):
    return f"{num:02}"

'''
##################################################################################################################################
#############################################     PRIMARY VARIABLE DECLARATIONS     ##############################################
##################################################################################################################################
'''

# set local path
cwd = os.getcwd()

# options
img_extensions = ["png", "jpg", "same_as_original"]
method_tag_files_opts = ["relocate", "copy"]
collect_checkboxes = ["include_tag_file", "include_explicit_tag", "include_questionable_tag", "include_safe_tag",
                      "include_png", "include_jpg", "include_gif", "include_webm", "include_swf", "include_explicit",
                      "include_questionable", "include_safe"]
download_checkboxes = ["skip_post_download", "reorder_tags", "replace_underscores", "remove_parentheses", "do_sort"]
resize_checkboxes = ["skip_resize", "delete_original"]

### assume settings.json at the root dir of repo

# session config
config_name = "settings.json"
global settings_json
settings_json = load_session_config(os.path.join(cwd, config_name))
global required_tags_list
required_tags_list = get_list(settings_json["required_tags"], settings_json["tag_sep"])
for tag in required_tags_list:
    if len(tag) == 0:
        required_tags_list.remove(tag)

global blacklist_tags
blacklist_tags = get_list(settings_json["blacklist"], " | ")
for tag in blacklist_tags:
    if len(tag) == 0:
        blacklist_tags.remove(tag)

verbose_print(f"{settings_json}")
verbose_print(f"json key count: {len(settings_json)}")

# UPDATE json with new key, value pairs
if not "min_date" in settings_json:
    settings_json["min_year"] = 2000
elif isinstance(settings_json["min_date"], str) and "-" in settings_json["min_date"]:
    settings_json["min_year"] = int(settings_json["min_date"].split("-")[0])
else:
    settings_json["min_year"] = int(settings_json["min_date"])

if not "min_month" in settings_json:
    settings_json["min_month"] = 1
elif isinstance(settings_json["min_date"], str) and "-" in settings_json["min_date"]:
    settings_json["min_month"] = from_padded(settings_json["min_date"].split("-")[1])

if not "min_day" in settings_json:
    settings_json["min_day"] = 1
elif isinstance(settings_json["min_date"], str) and settings_json["min_date"].count("-") > 1:
    settings_json["min_day"] = from_padded(settings_json["min_date"].split("-")[-1])

update_JSON(settings_json, config_name)

'''
##################################################################################################################################
#################################################     COMPONENT/S FUNCTION/S     #################################################
##################################################################################################################################
'''

def config_save_button(batch_folder,resized_img_folder,tag_sep,tag_order_format,prepend_tags,append_tags,img_ext,
                              method_tag_files,min_score,min_fav_count,min_area,top_n,min_short_side,
                              skip_posts_file,skip_posts_type,
                       collect_from_listed_posts_file,collect_from_listed_posts_type,apply_filter_to_listed_posts,
                       save_searched_list_type,save_searched_list_path,downloaded_posts_folder,png_folder,jpg_folder,
                       webm_folder,gif_folder,swf_folder,save_filename_type,remove_tags_list,replace_tags_list,
                       tag_count_list_folder,min_month,min_day,min_year,collect_checkbox_group_var,download_checkbox_group_var,resize_checkbox_group_var):
    global settings_json
    settings_json["batch_folder"] = str(batch_folder)
    settings_json["resized_img_folder"] = str(resized_img_folder)
    settings_json["tag_sep"] = str(tag_sep)
    settings_json["tag_order_format"] = str(tag_order_format)
    settings_json["prepend_tags"] = str(prepend_tags)
    settings_json["append_tags"] = str(append_tags)
    settings_json["img_ext"] = str(img_ext)
    settings_json["method_tag_files"] = str(method_tag_files)
    settings_json["min_score"] = int(min_score)
    settings_json["min_fav_count"] = int(min_fav_count)

    settings_json["min_year"] = int(min_year)
    settings_json["min_month"] = int(min_month)
    settings_json["min_day"] = int(min_day)

    settings_json["min_date"] = f"{int(min_year)}-{to_padded(int(min_month))}-{to_padded(int(min_day))}"

    settings_json["min_area"] = int(min_area)
    settings_json["top_n"] = int(top_n)
    settings_json["min_short_side"] = int(min_short_side)

    # COLLECT CheckBox Group
    for key in collect_checkboxes:
        if key in collect_checkbox_group_var:
            settings_json[key] = True
        else:
            settings_json[key] = False
    # DOWNLOAD CheckBox Group
    for key in download_checkboxes:
        if key in download_checkbox_group_var:
            settings_json[key] = True
        else:
            settings_json[key] = False
    # RESIZE CheckBox Group
    for key in resize_checkboxes:
        if key in resize_checkbox_group_var:
            settings_json[key] = True
        else:
            settings_json[key] = False

    settings_json["required_tags"] = get_string(required_tags_list, str(tag_sep))
    settings_json["blacklist"] = get_string(blacklist_tags, " | ")

    settings_json["skip_posts_file"] = str(skip_posts_file)
    settings_json["skip_posts_type"] = str(skip_posts_type)
    settings_json["collect_from_listed_posts_file"] = str(collect_from_listed_posts_file)
    settings_json["collect_from_listed_posts_type"] = str(collect_from_listed_posts_type)
    settings_json["apply_filter_to_listed_posts"] = bool(apply_filter_to_listed_posts)
    settings_json["save_searched_list_type"] = str(save_searched_list_type)
    settings_json["save_searched_list_path"] = str(save_searched_list_path)
    settings_json["downloaded_posts_folder"] = str(downloaded_posts_folder)
    settings_json["png_folder"] = str(png_folder)
    settings_json["jpg_folder"] = str(jpg_folder)
    settings_json["webm_folder"] = str(webm_folder)
    settings_json["gif_folder"] = str(gif_folder)
    settings_json["swf_folder"] = str(swf_folder)
    settings_json["save_filename_type"] = str(save_filename_type)
    settings_json["remove_tags_list"] = str(remove_tags_list)
    settings_json["replace_tags_list"] = str(replace_tags_list)
    settings_json["tag_count_list_folder"] = str(tag_count_list_folder)

    # Update json
    update_JSON(settings_json, config_name)

def text_handler_required(tag_string_comp):
    temp_tags = None
    if settings_json["tag_sep"] in tag_string_comp:
        temp_tags = tag_string_comp.split(settings_json["tag_sep"])
    elif " | " in tag_string_comp:
        temp_tags = tag_string_comp.split(" | ")
    else:
        temp_tags = [tag_string_comp]

    for tag in temp_tags:
        if not tag in required_tags_list:
            required_tags_list.append(tag)
    return gr.update(lines=1, label='Press Enter to ADD tag/s (E.g. tag1    or    tag1, tag2, ..., etc.)', value=""), \
           gr.update(choices=required_tags_list, label='ALL Required Tags', value=[])

def text_handler_blacklist(tag_string_comp):
    temp_tags = None
    if settings_json["tag_sep"] in tag_string_comp:
        temp_tags = tag_string_comp.split(settings_json["tag_sep"])
    elif " | " in tag_string_comp:
        temp_tags = tag_string_comp.split(" | ")
    else:
        temp_tags = [tag_string_comp]

    for tag in temp_tags:
        if not tag in blacklist_tags:
            blacklist_tags.append(tag)
    return gr.update(lines=1, label='Press Enter to ADD tag/s (E.g. tag1    or    tag1, tag2, ..., etc.)', value=""), \
           gr.update(choices=blacklist_tags, label='ALL Blacklisted Tags', value=[])

def check_box_group_handler_required(check_box_group):
    for tag in check_box_group:
        required_tags_list.remove(tag)
    return gr.update(choices=required_tags_list, label='ALL Required Tags', value=[])

def check_box_group_handler_blacklist(check_box_group):
    for tag in check_box_group:
        blacklist_tags.remove(tag)
    return gr.update(choices=blacklist_tags, label='ALL Blacklisted Tags', value=[])

### file expects a format of 1 tag per line, with the tag being before the first comma
def parse_file_required(file_list):
    for single_file in file_list:
        with open(single_file, 'r') as read_file:
            while True:
                line = read_file.readline()
                if not line:
                    break
                tag = line.replace(" ", "").split(",")[0]
                if not tag in required_tags_list:
                    required_tags_list.append(tag)
            read_file.close()
    return gr.update(choices=required_tags_list, label='ALL Required Tags', value=[])

### file expects a format of 1 tag per line, with the tag being before the first comma
def parse_file_blacklist(file_list):
    for single_file in file_list:
        with open(single_file, 'r') as read_file:
            while True:
                line = read_file.readline()
                if not line:
                    break
                tag = line.replace(" ", "").split(",")[0]
                if not tag in blacklist_tags:
                    blacklist_tags.append(tag)
            read_file.close()
    return gr.update(choices=blacklist_tags, label='ALL Blacklisted Tags', value=[])

def run_script(basefolder,settings_path,numcpu,phaseperbatch,keepdb,cachepostsdb,postscsv,tagscsv,postsparquet,tagsparquet,aria2cpath):
    run_cmd = f"python e621_batch_downloader.py"
    if len(basefolder) > 0:
        run_cmd += f" -f {basefolder}"
    run_cmd += f" -s {settings_path}"
    run_cmd += f" -c {numcpu}"
    if phaseperbatch:
        run_cmd += f" -ppb"
    if keepdb:
        run_cmd += f" -k"
    if cachepostsdb:
        run_cmd += f" -ch"
    if len(postscsv) > 0:
        run_cmd += f" -pcsv {postscsv}"
    if len(tagscsv) > 0:
        run_cmd += f" -tcsv {tagscsv}"
    if len(postsparquet) > 0:
        run_cmd += f" -ppar {postsparquet}"
    if len(tagsparquet) > 0:
        run_cmd += f" -tpar {tagsparquet}"
    if len(aria2cpath) > 0:
        run_cmd += f" -ap {aria2cpath}"

    verbose_print(f"RUN COMMAND IS:\t{run_cmd}")

    execute(run_cmd)

'''
##################################################################################################################################
#######################################################     GUI BLOCKS     #######################################################
##################################################################################################################################
'''

### The below CSS is dependent on the version of Gradio the user has, (gradio DEVs should have this fixed in the next version 22.0 of gradio)
cyan_button_css = "label.svelte-6iujhp.svelte-6iujhp.svelte-6iujhp {background: linear-gradient(#00ffff, #2563eb)}"
red_button_css = "label.svelte-6iujhp.svelte-6iujhp.svelte-6iujhp.selected {background: linear-gradient(#ff0000, #404040)}"
green_button_css = "label.svelte-6iujhp.svelte-6iujhp.svelte-6iujhp {background: linear-gradient(#2fa614, #2563eb)}"

with gr.Blocks(css=f"{green_button_css} {red_button_css}") as demo:
    with gr.Tab("General Config"):
        with gr.Row():
            config_save_var0 = gr.Button(value="Apply & Save Settings", variant='primary')
        gr.Markdown(
        """
        ### Make sure all necessary dependencies have been installed.
        ### Questions about certain features can be found here: https://github.com/pikaflufftuft/pikaft-e621-posts-downloader
        ### This UI currently works in the case of ( SINGLE ) batch configurations
        """)
        with gr.Row():
            with gr.Column():
                batch_folder = gr.Textbox(lines=1, label='Path to Batch Directory', value=settings_json["batch_folder"])
            with gr.Column():
                resized_img_folder = gr.Textbox(lines=1, label='Path to Resized Images', value=settings_json["resized_img_folder"])
        with gr.Row():
            tag_sep = gr.Textbox(lines=1, label='Tag Seperator/Delimeter', value=settings_json["tag_sep"])
            tag_order_format = gr.Textbox(lines=1, label='Tag ORDER', value=settings_json["tag_order_format"])
            prepend_tags = gr.Textbox(lines=1, label='Prepend Tags', value=settings_json["prepend_tags"])
            append_tags = gr.Textbox(lines=1, label='Append Tags', value=settings_json["append_tags"])
        with gr.Row():
            with gr.Column():
                img_ext = gr.Dropdown(choices=img_extensions, label='Image Extension', value=settings_json["img_ext"])
            with gr.Column():
                method_tag_files = gr.Radio(choices=method_tag_files_opts, label='Resized Img Tag Handler', value=settings_json["method_tag_files"])

    with gr.Tab("Stats Config"):
        with gr.Row():
            config_save_var1 = gr.Button(value="Apply & Save Settings", variant='primary')
        with gr.Row():
            min_score = gr.Slider(minimum=0, maximum=10000, step=1, label='Filter: Min Score', value=settings_json["min_score"])
        with gr.Row():
            min_fav_count = gr.Slider(minimum=0, maximum=10000, step=1, label='Filter: Min Fav Count', value=settings_json["min_fav_count"])
        with gr.Row():
            with gr.Column():
                min_year = gr.Slider(minimum=2000, maximum=2050, step=1, label='Filter: Min Year', value=int(settings_json["min_year"]))
                min_month = gr.Slider(minimum=1, maximum=12, step=1, label='Filter: Min Month',
                                     value=int(settings_json["min_month"]))
                min_day = gr.Slider(minimum=1, maximum=31, step=1, label='Filter: Min Day',
                                     value=int(settings_json["min_day"]))
        with gr.Row():
            min_area = gr.Slider(minimum=1, maximum=1000000, step=1, label='Filter: Min Area', value=settings_json["min_area"])
        with gr.Row():
            top_n = gr.Slider(minimum=0, maximum=10000, step=1, label='Filter: Top N', value=settings_json["top_n"])
        with gr.Row():
            min_short_side = gr.Slider(minimum=1, maximum=100000, step=1, label='Resize Param: Min Short Side', value=settings_json["min_short_side"])

    with gr.Tab("Checkbox Config"):
        with gr.Row():
            config_save_var2 = gr.Button(value="Apply & Save Settings", variant='primary')
        with gr.Row():
            with gr.Column():
                gr.Markdown(
                """
                ### Data Collection Options
                """)
                collect_checkbox_group_var = gr.CheckboxGroup(choices=collect_checkboxes, label='Collect Checkboxes', value=grab_pre_selected(settings_json, collect_checkboxes))
            with gr.Column():
                gr.Markdown(
                """
                ###  Data Download Options
                """)
                download_checkbox_group_var = gr.CheckboxGroup(choices=download_checkboxes, label='Download Checkboxes', value=grab_pre_selected(settings_json, download_checkboxes))
            with gr.Column():
                gr.Markdown(
                """
                ###  Data Resize Options
                """)
                resize_checkbox_group_var = gr.CheckboxGroup(choices=resize_checkboxes, label='Resize Checkboxes', value=grab_pre_selected(settings_json, resize_checkboxes))

    with gr.Tab("Required Tags Config"):
        with gr.Row():
            config_save_var3 = gr.Button(value="Apply & Save Settings", variant='primary')
        with gr.Row():
            with gr.Column():
                required_tags = gr.Textbox(lines=1, label='Press Enter to ADD tag/s (E.g. tag1    or    tag1, tag2, ..., etc.)', value="")
                remove_button_required = gr.Button(value="Remove Checked Tags", variant='secondary')
            with gr.Column():
                file_all_tags_list_required = gr.File(file_count="multiple", file_types=["file"], label="Select ALL files with Tags to be parsed and Added")
                parse_button_required = gr.Button(value="Parse/Add Tags", variant='secondary')
        with gr.Row():
            required_tags_group_var = gr.CheckboxGroup(choices=required_tags_list, label='ALL Required Tags', value=[])

    with gr.Tab("Blacklist Tags Config"):
        with gr.Row():
            config_save_var4 = gr.Button(value="Apply & Save Settings", variant='primary')
        with gr.Row():
            with gr.Column():
                blacklist = gr.Textbox(lines=1, label='Press Enter to ADD tag/s (E.g. tag1    or    tag1, tag2, ..., etc.)', value="")
                remove_button_blacklist = gr.Button(value="Remove Checked Tags", variant='secondary')
            with gr.Column():
                file_all_tags_list_blacklist = gr.File(file_count="multiple", file_types=["file"], label="Select ALL files with Tags to be parsed and Added")
                parse_button_blacklist = gr.Button(value="Parse/Add Tags", variant='secondary')
        with gr.Row():
            blacklist_group_var = gr.CheckboxGroup(choices=blacklist_tags, label='ALL Blacklisted Tags', value=[])

    with gr.Tab("Additional Components Config"):
        with gr.Row():
            config_save_var5 = gr.Button(value="Apply & Save Settings", variant='primary')
        with gr.Row():
            with gr.Column():
                skip_posts_file = gr.Textbox(lines=1, label='Path to file w/ multiple id/md5 to skip',
                                             value=settings_json["skip_posts_file"])
                skip_posts_type = gr.Radio(choices=["id","md5"], label='id/md5 skip', value=settings_json["skip_posts_type"])
            with gr.Column():
                save_searched_list_path = gr.Textbox(lines=1, label='id/md5 list to file path', value=settings_json["save_searched_list_path"])
                save_searched_list_type = gr.Radio(choices=["id", "md5", "None"], label='Save id/md5 list to file', value=settings_json["save_searched_list_type"])
        with gr.Row():
            with gr.Column():
                apply_filter_to_listed_posts = gr.Checkbox(label='Apply Filters to Collected Posts',
                                                   value=settings_json["apply_filter_to_listed_posts"])
                collect_from_listed_posts_type = gr.Radio(choices=["id", "md5"], label='id/md5 collect',
                                                          value=settings_json["collect_from_listed_posts_type"])
                collect_from_listed_posts_file = gr.Textbox(lines=1, label='Path to file w/ multiple id/md5 to collect',
                                                            value=settings_json["collect_from_listed_posts_file"])
        with gr.Row():
            downloaded_posts_folder = gr.Textbox(lines=1, label='Path for downloaded posts',
                                                 value=settings_json["downloaded_posts_folder"])
            png_folder = gr.Textbox(lines=1, label='Path for png data', value=settings_json["png_folder"])
            jpg_folder = gr.Textbox(lines=1, label='Path for jpg data', value=settings_json["jpg_folder"])
            webm_folder = gr.Textbox(lines=1, label='Path for webm data', value=settings_json["webm_folder"])
            gif_folder = gr.Textbox(lines=1, label='Path for gif data', value=settings_json["gif_folder"])
            swf_folder = gr.Textbox(lines=1, label='Path for swf data', value=settings_json["swf_folder"])
        with gr.Row():
            save_filename_type = gr.Radio(choices=["id","md5"], label='Select Filename Type', value=settings_json["save_filename_type"])
            remove_tags_list = gr.Textbox(lines=1, label='Path to negative tags file', value=settings_json["remove_tags_list"])
            replace_tags_list = gr.Textbox(lines=1, label='Path to replace tags file', value=settings_json["replace_tags_list"])
            tag_count_list_folder = gr.Textbox(lines=1, label='Path to tag count file', value=settings_json["tag_count_list_folder"])

    with gr.Tab("Run Tab"):
        with gr.Row():
            with gr.Column():
                basefolder = gr.Textbox(lines=1, label='Root Output Dir Path', value=cwd)
                settings_path = gr.Textbox(lines=1, label='Path to json', value=config_name)
                numcpu = gr.Slider(minimum=1, maximum=mp.cpu_count(), step=1, label='Worker Threads', value=int(mp.cpu_count()/2))
        with gr.Row():
            with gr.Column():
               phaseperbatch = gr.Checkbox(label='Completes all phases per batch', value=True)
            with gr.Column():
               keepdb = gr.Checkbox(label='Keep e6 db data', value=False)
            with gr.Column():
                cachepostsdb = gr.Checkbox(label='cache e6 posts file when multiple batches', value=False)
        with gr.Row():
            postscsv = gr.Textbox(lines=1, label='Path to e6 posts csv', value="")
            tagscsv = gr.Textbox(lines=1, label='Path to e6 tags csv', value="")
            postsparquet = gr.Textbox(lines=1, label='Path to e6 posts parquet', value="")
            tagsparquet = gr.Textbox(lines=1, label='Path to e6 tags parquet', value="")
            aria2cpath = gr.Textbox(lines=1, label='Path to aria2c program', value="")
        with gr.Row():
            run_button = gr.Button(value="Run", variant='primary')

    '''
    ##################################################################################################################################
    ####################################################     EVENT HANDLER/S     #####################################################
    ##################################################################################################################################
    '''

    config_save_var0.click(fn=config_save_button,
                          inputs=[batch_folder,resized_img_folder,tag_sep,tag_order_format,prepend_tags,append_tags,
                                  img_ext,method_tag_files,min_score,min_fav_count,min_area,top_n,
                                  min_short_side,skip_posts_file,
                                  skip_posts_type,collect_from_listed_posts_file,collect_from_listed_posts_type,
                                  apply_filter_to_listed_posts,save_searched_list_type,save_searched_list_path,
                                  downloaded_posts_folder,png_folder,jpg_folder,webm_folder,gif_folder,swf_folder,
                                  save_filename_type,remove_tags_list,replace_tags_list,tag_count_list_folder,min_month,
                                  min_day,min_year,collect_checkbox_group_var,download_checkbox_group_var,resize_checkbox_group_var
                                  ],
                          outputs=[]
                          )
    config_save_var1.click(fn=config_save_button,
                          inputs=[batch_folder,resized_img_folder,tag_sep,tag_order_format,prepend_tags,append_tags,
                                  img_ext,method_tag_files,min_score,min_fav_count,min_area,top_n,
                                  min_short_side,skip_posts_file,
                                  skip_posts_type,collect_from_listed_posts_file,collect_from_listed_posts_type,
                                  apply_filter_to_listed_posts,save_searched_list_type,save_searched_list_path,
                                  downloaded_posts_folder,png_folder,jpg_folder,webm_folder,gif_folder,swf_folder,
                                  save_filename_type,remove_tags_list,replace_tags_list,tag_count_list_folder,min_month,
                                  min_day,min_year,collect_checkbox_group_var,download_checkbox_group_var,resize_checkbox_group_var
                                  ],
                          outputs=[]
                          )
    config_save_var2.click(fn=config_save_button,
                          inputs=[batch_folder,resized_img_folder,tag_sep,tag_order_format,prepend_tags,append_tags,
                                  img_ext,method_tag_files,min_score,min_fav_count,min_area,top_n,
                                  min_short_side,skip_posts_file,
                                  skip_posts_type,collect_from_listed_posts_file,collect_from_listed_posts_type,
                                  apply_filter_to_listed_posts,save_searched_list_type,save_searched_list_path,
                                  downloaded_posts_folder,png_folder,jpg_folder,webm_folder,gif_folder,swf_folder,
                                  save_filename_type,remove_tags_list,replace_tags_list,tag_count_list_folder,min_month,
                                  min_day,min_year,collect_checkbox_group_var,download_checkbox_group_var,resize_checkbox_group_var
                                  ],
                          outputs=[]
                          )
    config_save_var3.click(fn=config_save_button,
                          inputs=[batch_folder,resized_img_folder,tag_sep,tag_order_format,prepend_tags,append_tags,
                                  img_ext,method_tag_files,min_score,min_fav_count,min_area,top_n,
                                  min_short_side,skip_posts_file,
                                  skip_posts_type,collect_from_listed_posts_file,collect_from_listed_posts_type,
                                  apply_filter_to_listed_posts,save_searched_list_type,save_searched_list_path,
                                  downloaded_posts_folder,png_folder,jpg_folder,webm_folder,gif_folder,swf_folder,
                                  save_filename_type,remove_tags_list,replace_tags_list,tag_count_list_folder,min_month,
                                  min_day,min_year,collect_checkbox_group_var,download_checkbox_group_var,resize_checkbox_group_var
                                  ],
                          outputs=[]
                          )
    config_save_var4.click(fn=config_save_button,
                          inputs=[batch_folder,resized_img_folder,tag_sep,tag_order_format,prepend_tags,append_tags,
                                  img_ext,method_tag_files,min_score,min_fav_count,min_area,top_n,
                                  min_short_side,skip_posts_file,
                                  skip_posts_type,collect_from_listed_posts_file,collect_from_listed_posts_type,
                                  apply_filter_to_listed_posts,save_searched_list_type,save_searched_list_path,
                                  downloaded_posts_folder,png_folder,jpg_folder,webm_folder,gif_folder,swf_folder,
                                  save_filename_type,remove_tags_list,replace_tags_list,tag_count_list_folder,min_month,
                                  min_day,min_year,collect_checkbox_group_var,download_checkbox_group_var,resize_checkbox_group_var
                                  ],
                          outputs=[]
                          )
    config_save_var5.click(fn=config_save_button,
                          inputs=[batch_folder,resized_img_folder,tag_sep,tag_order_format,prepend_tags,append_tags,
                                  img_ext,method_tag_files,min_score,min_fav_count,min_area,top_n,
                                  min_short_side,skip_posts_file,
                                  skip_posts_type,collect_from_listed_posts_file,collect_from_listed_posts_type,
                                  apply_filter_to_listed_posts,save_searched_list_type,save_searched_list_path,
                                  downloaded_posts_folder,png_folder,jpg_folder,webm_folder,gif_folder,swf_folder,
                                  save_filename_type,remove_tags_list,replace_tags_list,tag_count_list_folder,min_month,
                                  min_day,min_year,collect_checkbox_group_var,download_checkbox_group_var,resize_checkbox_group_var
                                  ],
                          outputs=[]
                          )

    run_button.click(fn=run_script,
                     inputs=[basefolder,settings_path,numcpu,phaseperbatch,keepdb,cachepostsdb,postscsv,tagscsv,
                             postsparquet,tagsparquet,aria2cpath],
                     outputs=[])

    required_tags.submit(fn=text_handler_required, inputs=[required_tags], outputs=[required_tags,required_tags_group_var])
    blacklist.submit(fn=text_handler_blacklist, inputs=[blacklist], outputs=[blacklist,blacklist_group_var])

    remove_button_required.click(fn=check_box_group_handler_required, inputs=[required_tags_group_var], outputs=[required_tags_group_var])
    remove_button_blacklist.click(fn=check_box_group_handler_blacklist, inputs=[blacklist_group_var], outputs=[blacklist_group_var])

    parse_button_required.click(fn=parse_file_required, inputs=[file_all_tags_list_required], outputs=[required_tags_group_var])
    parse_button_blacklist.click(fn=parse_file_blacklist, inputs=[file_all_tags_list_blacklist], outputs=[blacklist_group_var])

if __name__ == "__main__":
    # init client & server connection
    HOST = "127.0.0.1"

    demo.launch()