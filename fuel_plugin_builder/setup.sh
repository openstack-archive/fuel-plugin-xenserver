set -x

VIRENV_PATH=${1:-"../../MOS"}
FPB_PATH=${2:-"../../fuel-plugins"}

[ -e "$VIRENV_PATH/bin/activate" ] ||	virtualenv "$VIRENV_PATH"

source $VIRENV_PATH/bin/activate

[ -e "$FPB_PATH" ] || git clone "https://github.com/stackforge/fuel-plugins.git" "$FPB_PATH"


if [[ -z `pip show fuel-plugin-builder` ]] ; then 
	cp plugin_rpm.spec.mako "$FPB_PATH/fuel_plugin_builder/fuel_plugin_builder/templates/v2/build/plugin_rpm.spec.mako"
	sudo pip install -e "$FPB_PATH/fuel_plugin_builder"
fi

#echo `which fpb`