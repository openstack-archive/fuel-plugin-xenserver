set -x

ACTION=${1:-"install"}

cd ..
source localrc

[ -e "$VIRENV_PATH/bin/activate" ] ||	virtualenv "$VIRENV_PATH"

source $VIRENV_PATH/bin/activate

[ -e "$FPB_PATH" ] || git clone "https://github.com/stackforge/fuel-plugins.git" "$FPB_PATH"

if [[ $ACTION == "overwrite" ]] ; then 
	cp plugin_rpm.spec.mako "$FPB_PATH/fuel_plugin_builder/fuel_plugin_builder/templates/v2/build/plugin_rpm.spec.mako"
fi

if [[ -z `pip show fuel-plugin-builder` ]] ; then 
	cp plugin_rpm.spec.mako "$FPB_PATH/fuel_plugin_builder/fuel_plugin_builder/templates/v2/build/plugin_rpm.spec.mako"
	sudo pip install -e "$FPB_PATH/fuel_plugin_builder"
fi

echo `which fpb`