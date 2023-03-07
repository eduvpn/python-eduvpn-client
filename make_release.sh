#!/bin/sh

# This script was adapted from fkooman: https://git.sr.ht/~fkooman/vpn-daemon/tree/main/item/make_release.sh. Thanks!
#
# Make a release of the latest tag, or of the tag/branch/commit specified as
# the first parameter.
#

# Fail if error
set -e

PROJECT_NAME=$(basename "${PWD}")
PROJECT_VERSION=${1}
RELEASE_DIR="${PWD}/release"
KEY_ID=227FF3F8F829D9A9314D9EBA02BB8048BBFF222C

mkdir -p "${RELEASE_DIR}"

if [ -z "${1}" ]; then
    # we take the last "tag" of the Git repository as version
    PROJECT_VERSION=$(git describe --abbrev=0 --tags)
    echo Version: "${PROJECT_VERSION}"
fi

if [ -f "${RELEASE_DIR}/${PROJECT_NAME}-${PROJECT_VERSION}.tar.xz" ]; then
    echo "Version ${PROJECT_VERSION} already has a release!"

    exit 1
fi

# Archive repository
git archive --prefix "${PROJECT_NAME}-${PROJECT_VERSION}/" "${PROJECT_VERSION}" | tar -xf -

# Tar
tar -cJf "${RELEASE_DIR}/${PROJECT_NAME}-${PROJECT_VERSION}.tar.xz" "${PROJECT_NAME}-${PROJECT_VERSION}"
rm -rf "${PROJECT_NAME}-${PROJECT_VERSION}"

# Sign
echo "signing using gpg and minisign"
gpg --default-key ${KEY_ID} --armor --detach-sign "${RELEASE_DIR}/${PROJECT_NAME}-${PROJECT_VERSION}.tar.xz"
minisign -Sm "${RELEASE_DIR}/${PROJECT_NAME}-${PROJECT_VERSION}.tar.xz"
