# this script should work on both Linux and *BSD

source authdata.conf

function rawurlencode {
    local string="${1}"
    local strlen=${#string}
    local encoded=""

    # not supported by *BSD, but usually not neccessary on Arm64
    local endianness=$([ `uname -s` == Linux ] && echo -n ' --endian=big')
    local pos c o g

    for (( pos=0 ; pos<strlen ; pos++ )); do
	c=${string:$pos:1}
	g=$(echo -n "${c}" | LC_ALL=C grep -Ee "[-_.~a-zA-Z0-9]")
	case "$g" in
            $c) o="${c}" ;;
            * ) o=$(echo -n "${c}" | od -t x1 $endianness -A n -v \
			| tr "[:lower:]" "[:upper:]" | xargs | tr -d ' \n' \
			| sed -r 's/(.{2})/\%\1/g')
     esac
     encoded+="${o}"
  done
  echo "${encoded}"
}

function make_auth_token {
    local consumer_key_safe=`rawurlencode "${CONSUMER_KEY}"`
    local consumer_secret_safe=`rawurlencode "${CONSUMER_SECRET}"`
    echo -n "${consumer_key_safe}:${consumer_secret_safe}" | base64 | tr -d '\n'
}

function obtain_bearer_token {
    local bearer=""
    local token_file="${CONFIG_DIR}/access_token"
    local URL="https://api.twitter.com/oauth2/token"

    if test -e $token_file; then
	bearer=$(<$token_file)
    else
	local auth_token=`make_auth_token`
	local payload="grant_type=client_credentials"

	local response=$(curl -v\
			-H "Authorization: Basic ${auth_token}"\
			-H "Accept-Encoding: gzip"\
			-H "Content-Type: application/x-www-form-urlencoded;charset=UTF-8"\
			-X POST -d ${payload} ${URL} | zcat)
	bearer=`echo $response | jq .access_token -r`
	echo -n $bearer > $token_file
    fi
    echo $bearer
}

function get_trends {
    local bearer_token=`obtain_bearer_token`
    local woeid=$(<"$CONFIG_DIR/woeid")
    local response=$(curl -v --raw\
	 -X GET\
	 -H "Authorization: Bearer ${bearer_token}"\
	 -H "Accept-Encoding: gzip"\
	 "https://api.twitter.com/1.1/trends/place.json?id=${woeid}" | zcat)
    local trends=$(echo $response | jq '.[].trends | .[].name' -r)

    local new_trends=()
    index=0
    OLD_IFS=$IFS
    IFS=$'\n'
    for object in $trends; do
	local keyword_safe=`sql_esc ${object#'#'}` # removed hashtag
	if test 0 -ne $(sqlite3 $CONFIG_DIR/botdb "select count(*) from blacklist where
	 keyword like '%${keyword_safe}%';"); then
	    continue;
	fi
	new_trends[$index]=`filter_trends "${object}"`
	((index++))
    done
    IFS=$OLD_IFS

    echo ${new_trends[@]}
}

function compose_tweet {
    local timestamp=`date +%s`
    local signature_method="HMAC-SHA1"
    local nonce=`generate_nonce`
    local oauth_version="1.0"
    local status=$1
    local urlupdate="https://api.twitter.com/1.1/statuses/update.json"

    local signature=`build_oauth_signature $status $nonce $signature_method $timestamp $OAUTH_TOKEN $oauth_version POST $urlupdate`
    local signature_safe=`rawurlencode "${signature}"`

    local status_safe=`rawurlencode "${status}"`

    local auth_header="OAuth \
oauth_consumer_key=\"${CONSUMER_KEY}\", \
oauth_nonce=\"${nonce}\", \
oauth_signature=\"${signature_safe}\", \
oauth_signature_method=\"${signature_method}\", \
oauth_timestamp=\"${timestamp}\", \
oauth_token=\"${OAUTH_TOKEN}\", \
oauth_version=\"${oauth_version}\""

    local payload="status=${status_safe}"

    curl -v\
	 -H "Authorization: ${auth_header}"\
	 -X POST -d ${payload}\
	 -H "Accept-Encoding: gzip"\
	 $urlupdate | zcat
}

# parameters: key, value
function hmac_sha1 {
    echo -n "${2}" | openssl sha1 -hmac "${1}" -binary | base64 | tr -d '\n'
}

# parameters: status, nonce, sign-method, timestamp, token, version, http_method, url
function build_oauth_signature {
    local include_entities="true"
    local oauth_consumer_key=`rawurlencode $CONSUMER_KEY`
    local oauth_nonce=`rawurlencode $2`
    local oauth_signature_method=`rawurlencode $3`
    local oauth_timestamp=`rawurlencode $4`
    local oauth_token=`rawurlencode $5`
    local oauth_version=`rawurlencode $6`
    local status=`rawurlencode $1`

    local http_method=$7
    local http_method_upper=${http_method^^}
    local url_enc=`rawurlencode $8`

    # alphabetically
    local parameters="\
oauth_consumer_key=${oauth_consumer_key}&\
oauth_nonce=${oauth_nonce}&\
oauth_signature_method=${oauth_signature_method}&\
oauth_timestamp=${oauth_timestamp}&\
oauth_token=${oauth_token}&\
oauth_version=${oauth_version}&\
status=${status}"

    local parameters_encoded=`rawurlencode $parameters`
    local base="${http_method_upper}&${url_enc}&${parameters_encoded}"

    local consumer_secret_encoded=`rawurlencode $CONSUMER_SECRET`
    local oauth_secret_encoded=`rawurlencode $OAUTH_SECRET`
    local signing_key="${consumer_secret_encoded}&${oauth_secret_encoded}"

    hmac_sha1 $signing_key $base
}

function generate_nonce {
    dd if=/dev/random bs=1 count=32 2>/dev/null \
	| base64 | tr -d '\n' | grep -e "[0-9a-z]*" -io | tr -d '\n'
}
