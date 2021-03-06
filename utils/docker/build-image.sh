#!/usr/bin/env bash


function print_usage(){
    (   echo "USAGE: $0 [-o|--image-owner OWNER] [-n|--image-name NAME] [-t|--image-tag TAG] < minimal | develop >"
        echo
        echo "If no arguments are provided, this script will try to get the"
        echo "required repository information from the local repository itself") >&2
}

# parse args
while test $# -gt 0
do
    case "$1" in
        -h|--help)
            print_usage
            exit 0
            ;;
        -r|--image-registry)
            export IMAGE_REGISTRY=$2
            shift
            ;;
        -o|--image-owner)
            export IMAGE_OWNER=$2
            shift
            ;;
        -n|--image-name)
            export IMAGE_NAME=$2
            shift
            ;;
        -t|--image-tag)
            export IMAGE_TAG=$2
            shift
            ;;
        --url|--repo-url)
            repo_url="--url $2"
            shift
            ;;
        --branch|--repo-branch)
            repo_branch="--branch $2"
            shift
            ;;
        --*)
            print_usage
            exit 99
            ;;
        *)
            # support only the first argument; skip all remaining
            if [[ -z ${image_type} ]]; then
                image_type=${1}
            fi
            ;;
    esac
    shift
done

if [[ -z ${image_type} ]]; then
    image_type="minimal"
    echo "No image type provided. Using the default : ${image_type}">&2
elif [[ ${image_type} != "minimal" && ${image_type} != "develop" ]]; then
    echo -e "\nERROR: '${image_type}' not supported! Use 'minimal' or 'develop'."
    exit 99
else
    export IMAGE_TYPE="${image_type}"
fi

# absolute path of the current script
script_path="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# absolute path of the image folder
image_path="${script_path}/${image_type}"
# check whether the image type exists
if [[ ! -d ${image_path} ]]; then
    echo -e "\nThe image type '${image_type}' doen't exist!!!"
    exit 99
fi

# set git && image info
source ${script_path}/set-git-repo-info.sh ${repo_url} ${repo_branch}
source ${script_path}/set-docker-image-info.sh

# Need to cd into this script's directory because image-config assumes it's running within it
cd "${image_path}" > /dev/null

# build the Docker image
docker build --build-arg git_branch=${GIT_BRANCH} --build-arg git_url=${GIT_HTTPS} -t ${IMAGE} .

# restore the original path
cd - > /dev/null
