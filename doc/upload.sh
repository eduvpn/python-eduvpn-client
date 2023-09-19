#!/bin/sh

set -e

# Add these lines to ${HOME}/.ssh/known-hosts (without leading "#")
#ams-cdn.eduvpn.org ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIJXDSpq0Q17KijNPTEvhKPDSnx6WC73giHaYidD8eZk2
#eduvpn-cdn-2.deic.dk ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIEFcLZ2N48aiTQ3o6Du9K9OuVfP+/S5BD4DJH/aRwqFr

UPLOAD_SERVER_PATH_LIST="
    docs@ams-cdn.eduvpn.org:/var/www/docs.eduvpn.org/client/linux
    docs@eduvpn-cdn-2.deic.dk:/var/www/docs.eduvpn.org/client/linux
"

for UPLOAD_SERVER_PATH in ${UPLOAD_SERVER_PATH_LIST}; do
	echo "${UPLOAD_SERVER_PATH}..."
	rsync -e ssh -rltO --delete site/ "${UPLOAD_SERVER_PATH}" --progress --exclude '.git' || echo "FAIL ${SERVER}"
done
