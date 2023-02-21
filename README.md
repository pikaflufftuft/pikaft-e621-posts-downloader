# e621 Posts Downloader

![visitor badge](https://visitor-badge.glitch.me/badge?page_id=pikaflufftuft.pikaft-e621-posts-downloader)
 
 [![](https://img.shields.io/static/v1?message=Open%20in%20Colab&logo=googlecolab&labelColor=5c5c5c&color=0f80c1&label=%20&style=for-the-badge)](coming_soon) (coming soon!)

##### If you want to see post previews I recommend using Grabber https://github.com/Bionus/imgbrd-grabber

## Features

- Highly customizable settings
- Tag files processing
- Image resizing by minimum shortest side
- Fast, simple, and straightforward to use
- No rate limiting

## Requirements
python 3.8+

clone repository
```
git clone https://github.com/pikaflufftuft/pikaft-e621-posts-downloader.git
```
```
cd pikaft-e621-posts-downloader
pip install -r requirements.txt
```

#### aria2
This downloader uses aria2 for fast downloading.
```
sudo apt-get install aria2
```
For Windows, install the aria2 build https://github.com/aria2/aria2/releases/ Add aria2 in your evironment variables

## How to use

#### Customizing Posts Download Batches
Edit the setting parameters in `settings.json` in a text editor.
To create different parameter settings for multiple batches, use `[]` and separate each value with commas.

Example: The following will download posts that have the female tag with a minimum score of 100 in the first batch and posts that have the male tag with a min_score of 200 in the second batch.
```
"required_tags": ["female","male"],
"min_score": [100,200],
```

Not using `[]` will make the parameter setting be used for all batches, e.g., `"required_tags": "female",` will be used for each batch.

For all settings that use `[]`, they should use the same number of items, e.g.,

`"min_score": [100,200],` along with `"min_date": ["2016","2017","2018"],` will throw an error.

### Executing
| Flag | Argument | Description | Default |
| --- | --- | --- | --- |
| `-f` | `--basefolder` | default output directory used for storing e621 db files and downloading posts | *current working directory* |
| `-s` | `--settings` | (required) path to custom download settings json |  |
| `-c` | `--numcpu` | number of cpu to use for image resizing, set to -1 for max | -1 |
| `-ppb` | `--phaseperbatch` | performing all phases per batch as opposed to completing all batches per phase, e.g., if passed, complete all phases for the current batch before proceeding to the next batch, else, complete posts collection phase before downloading | *not passed* |
| `-pcsv` | `--postscsv` | path to e621 posts csv |  |
| `-tcsv` | `--tagscsv` | path to e621 tags csv |  |
| `-ppar` | `--postsparquet` | path to e621 posts parquet |  |
| `-tpar` | `--tagsparquet` | path to e621 tags parquet |  |

Example:

```
python3 e621_batch_downloader.py -s settings.json --phaseperbatch
```
I recommend passing `--phaseperbatch` for small storage spaces as thousands of posts can take up a lot of space. This completes batches one by one, resizing images in the current batch before downloading the next batch.

I recommend **not** passing it if you have adequate storage space and memory.

Posts/Tags parquets will be checked first then, when not found, will be created using posts/tags CSVs. <br />
Posts/Tags CSVs when not found, will be created using posts/tags CSV.gz's. <br />
Posts/Tags CSV.gz's when not found, will be downloaded.
### Setting parameters

| Parameter | type | Options | Description | Relative Parent folder |
|:--- |:---:|:---:|:--- |:---:|
| batch_folder | str | *any directory path* | Output directory for each batch | basefolder |
| required_tags | str | *any e621 tag* | Separate tags with `,`<br />combine multiple tag groups with <code>&#124;</code><br />example: get posts that are tagged either `anthro, wolf` or `feral, 4_toes` (or both):<br /><code>anthro, wolf &#124; feral, 4_toes</code><br />search for posts that starts/ends with a certain word by adding `*` after/before the word<br />example: `detailed*` includes tags such as `detailed`, `detailed_background`, `detailed_fur`, etc. |  |
| blacklist | str | *any e621 tag* | Uses the same format as `required_tags`. Blacklist tag groups found as a subset in any tag group in `required_tags` are ignored. Example: `female` and `female, anthro` are subsets of `female, anthro` but `female, anthro, male` and `female, male` are not. |  |
| include_png<br />include_jpg<br />include_gif<br />include_webm<br />include_swf | bool | `true`, `false` | Setting to `false` will not include posts with that file type. At least one should be `true`. |  |
| include_explicit<br />include_questionable<br />include_safe | bool | `true`, `false` | Setting to `false` will not include posts with that post rating. At least one should be `true`. |  |
| min_score | int |  | Collect posts with a minimum specified score |  |
| min_fav_count | int |  | Collect posts with a minimum specified favorite count |  |
| min_date | str |  | Collect posts starting from specified date. Use date format `YYYY-mm-dd` or `YYYY-mm` or `YYYY`. Use zero padding. |  |
| min_area | int |  | Collect posts with a minimum specified image dimension area. e.g., 512x512 = 262144. swf type posts are ignored. Set to `-1` to include any dimension areas |  |
| skip_posts_file | str | *any file path* | Path to a txt file containing a list of id/md5 of posts to skip (one post per line). Set to empty string to disable | basefolder |
| skip_posts_type | str | `"id"`, `"md5"` | Whether the content of `skip_posts_file` are id or md5 values |  |
| do_sort | bool | `true`, `false` | Sort posts by score in descending order. Posts are sorted by id (or date) in ascending order by default.  |  |
| top_n | int |  | Collect top n posts according to sort. If n > number of filtered posts, save all. Set to `-1` to save all  |  |
| save_searched_list_type | str | `"id"`, `"md5"`, `"None"` | Save a list of searched ids / md5s. Great for keeping track of what you've already searched for. Set to `"None"` to disable. |  |
| save_searched_list_path | str | *any file path* | File path/filename of list of searched ids / md5s. Default filenames: `list_of_searched_id.txt` / `list_of_searched_md5.txt` | batch_folder |
| downloaded_posts_folder | str | *any directory path* | Folder path for downloaded posts of any file type | batch_folder |
| png_folder<br />jpg_folder<br />gif_folder<br />webm_folder<br />swf_folder | str | *any directory path*  | Folder path for downloaded posts of that specific file type. Setting to empty string will default to `downloaded_posts_folder`. | downloaded_posts_folder |
| save_filename_type | str | `"id"`, `"md5"` | Downloaded posts filename type |  |
| include_tag_file | bool | `true`, `false` | Download posts along with their tags saved in .txt files. Tag files use `save_filename_type` as the filename but with a .txt extension |  |
| skip_post_download | bool | `true`, `false` | Set to `true` to not download collected posts. Good for when you only need to save tag files. |  |
| tag_sep | str |  | Separator used for separating tags in the tag file. `", "` is recommended.  |  |
| include_explicit_tag<br />include_questionable_tag<br />include_safe_tag | bool | `true`, `false` | Prepend post rating to tag list using the following tags representing `e`, `q`, `s`, respectively: `explicit`, `questionable`,`safe` |  |
| reorder_tags | bool | `true`, `false` | If `true`, rearrange tags into their respective categories specified in `tag_order_format` |  |
| tag_order_format | str | [e621 tag categories](https://github.com/pikaflufftuft/pikaft-e621-posts-downloader#e621-tag-categories) | Tag categories not listed will be removed from the tag file. If `reorder_tags` is `true`, this defines the tag category arrangment in the tag file. e.g., `"tag_order_format": "character, species",` species tags are placed after character tags. Specify at least one tag category. |  |
| prepend_tags<br />append_tags | str |  | Inserted at the start/end of the tag file. Use specified tag separator `tag_sep`. Unaffected by reordering of tags. Does not prepend/append if the custom tag is already present. Set to empty string to disable. |  |
| replace_underscores | bool | `true`, `false` | If `true`, replace underscores in tags with whitespaces |  |
| remove_parentheses | bool | `true`, `false` | If `true`, remove parentheses in tags |  |
| remove_tags_list | str | *any file path* | Path to a txt file containing a list of tags to remove from the tag file (one tag per line). Set to empty string to disable. | basefolder |
| replace_tags_list | str | *any file path* | Path to a txt/csv file containing a text pair separated with comma to replace specific tags from the tag file (one text pair per line). File content example:<br />`female,girl`<br />`male,boy`<br />All `female` tag instances will be replaced with `girl` and `male` with `boy`. The whole tag is considered. `female_anthro` will **not** be replaced into `girl_anthro`.  Set to empty string to disable. | basefolder |
| tag_count_list_folder | str | *any directory path* | Track the number of instances of each tag and save it into a CSV file sorted by count in descending order then by tag alphabetically. Each tag category specified in `tag_order_format` will also have a tag count CSV file. Tags in tag count CSV are unaffected by `replace_underscores` and `remove_parentheses`. | batch_folder |
| skip_resize | bool | `true`, `false` | If `true`, skips resizing of images. |  |
| min_short_side | int |  | Resize image if shortest side is longer than specified. e.g.,<br />minimum: 768px<br />img res: 1300x1698<br />resized res: 768x1003<br />I recommend using long enough lengths such as 512px (768px better) to minimize rounding error. Minimum positive value: `320`. Set to `-1` to disable resizing (not the same as `skip_resize`) and proceed with the following image processing. Images failed to resize are skipped. |  |
| img_ext | str | `"png"`, `"jpg"`, `".png"`, `".jpg"`, `"same_as_original"` | Image file extension for saving in image processing. If `min_short_side` is `-1` and `delete_original` is `false`, save a copy of the image in this image file extension. |  |
| delete_original | bool | `true`, `false` | If `false`, save resized image into the resized images folder specified in `resized_img_folder`. Create a copy of the original if it was not resized. |  |
| resized_img_folder | str | *any directory path* | Folder path to resized images. Set to empty string to use the same images path. If the resized image destination folder is where the original image is saved, the original image filename is prepended with `_` | batch_folder |
| method_tag_files | str | `"relocate"`, `"copy"` | If `delete_original` is `false` and the resized images folder is not the original images folder, relocate/copy the tag files to the resized images folder. |  |

#### File and Folder Paths
Whether it's a file or a folder path, you can specify either a relative path or an absolute path. Each parameter that is a relative path uses the specified parent folder in each batch accordingly.

##### Default folder directory tree
```
base_folder/
├─ batch_folder/
│  ├─ downloaded_posts_folder/
│  │  ├─ png_folder/
│  │  ├─ jpg_folder/
│  │  ├─ gif_folder/
│  │  ├─ webm_folder/
│  │  ├─ swf_folder/
│  ├─ resized_img_folder/
│  ├─ tag_count_list_folder/
│  │  ├─ tags.csv
│  │  ├─ tag_category.csv
│  ├─ save_searched_list_path.txt
```
Any file path parameter that are empty will use the default path.

Files/folders that use the same path are merged, not overwritten. For example, using the same path for save_searched_list_path at every batch will result in a combined searched list of every batch in one .txt file.

#### e621 tag categories:    
* general (`anthro`, `female`, `solo`, ...)
* artist (`tom_fischbach`, `unknown_artist`, ...)
* copyright (`nintendo`, `pokemon`, `disney`, ...)
* character (`loona_(helluva_boss)`, `legoshi_(beastars)`, ...)
* species (`canine`, `fox`, `dragon`, ...)
* invalid (`spooky_(disambiguation)`, ...)
* meta (`hi_res`, `digital_media_(artwork)`, ...)
* lore (`trans_(lore)`, `male_(lore)`, ...)
* rating (`explicit`, `questionable`, `safe`) (rating tags are techincally not e621 tags)

## License

MIT

## Usage conditions
By using this downloader, the user agrees that the author is not liable for any misuse of this downloader. This downloader is open-source and free to use.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
