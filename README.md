# MLABweb

MLAB home page with the interactive catalog of [MLAB modules](https://github.com/MLAB-modules).


## Usage

Individual entries in the module catalog are shown on the website based on two assumptions:
 - The module is located in the [MLAB-modules](https://github.com/MLAB-modules) GitHub organization.
 - The module contains a yaml file with metadata for display on the website. The file must be located at `/doc/metadata.yaml` (see the [MODUL01](https://github.com/mlab-modules/MODUL01) template repository, which is used to create new modules and already includes this file).

Once these conditions are met, the module will be shown on the website automatically. Displaying or refreshing the data may take some time. If nothing happens within an hour of making the change, the possible issues should be investigated, or the website administrator should be contacted.


### Automatic data update
To minimize the number of steps needed to get a module shown on the website, we try to automate as much of the process as possible. This is handled by GitHub Actions workflows that we wrote for this purpose. These workflows are typically updated by keeping a submodule, [/doc/assets/](https://github.com/MLAB-project/documents), in each module repository, which contains the individual actions needed for the repository to work correctly.


### Metadata yaml

Below is the basic structure of the yaml file.
The `<G:` flag marks a value that is generated automatically by GitHub Actions. This value can be automatically overwritten at any time.
The `<U:` flag marks a value that is entered by the user.

```
description: <G: Module description, about 250 characters, generated from the GitHub description>
github_branch: <G: Default branch on GitHub>
github_branches: 
- <G: List of branches in the repository>
github_repo: <G: Repository name>
github_url: <G: URL address of the repository>
homepage: <U: true/false, should the module be shown on the website's homepage?>
image_title: <U: Which image should be shown in the module overview?>
images:
- <G: List of images in the repository>
issues: <G: Number of open issues>
mark: <U: Quality rating of the module, a number 0-100)
mod_ibom: <G: Path to the ibom file>
mod_scheme: <G: Path to the schematic>
tags:
- <G: List of tags, generated from GitHub topics>
title: <G: Module name - generated from the repository name>
updated: <G: Time of the last update>
```

#### Module status and quality
The website has a green bar and a filter that can be used to select modules by status:
![image](https://github.com/MLAB-project/MLABweb/assets/5196729/8b603185-a976-4acb-b256-cd5631cbcdd0)

This corresponds to the `status` parameter in the yaml file, which can have a value of 1-5; if it is not specified, 2 is applied.
Value 4 (replaced) is set automatically by the webserver if the module has the [replaced](https://github.com/mlab-modules/USB232R01/blob/USB232R01B/doc/metadata.yaml#L24) attribute set.

There is also the `mark` value, which is likewise meant to reflect the state of the module in terms of how good its documentation is and how complete the module is. However, there is no defined description of what corresponds to which number. It is a range of 0-100; modules with good documentation seem to get a rating around 80-90 (I leave some headroom there). This number is assumed to drive the default sort order on the website.

Another parameter is `homepage: true/false`, which causes the module to be shown on the homepage. There, the estimate is that there should be no more than about 12 modules.

### Categories
The website shows a preselected set of categories that are linked to GitHub topics. The list of categories shown in the top menu is [here](/src/MLABweb/categories.py). In the metadata file, this corresponds to the `tags` entry.
