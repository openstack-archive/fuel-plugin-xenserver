#!/bin/bash
set -eu

# Source the branding file
. ${1}

# Find shortest delta
my_merge_base=$(git merge-base HEAD origin/master)

shortest_branch=master
for branch in $PLUGIN_BRANCHES; do

    # Verify that the named branch actually exists
    set +e
    git rev-parse --verify origin/$branch >/dev/null 2>/dev/null
    branch_test_exit_code=$?
    set -e
    if [ $branch_test_exit_code -gt 0 ]; then
        continue
    fi

    branch_merge_base=$(git merge-base origin/master origin/$branch)

    if [ "$branch_merge_base" == "$my_merge_base" ]; then
        shortest_branch=$branch
    fi
done

var_name=PLUGIN_VERSION_${shortest_branch//./_}
branch_merge_base=$(git merge-base origin/master origin/$shortest_branch)
branch_major=${!var_name}
if [ $shortest_branch == 'master' ]; then
    branch_minor=$(git rev-list HEAD --count)
else
    branch_minor=$(git rev-list HEAD ^$branch_merge_base --count)
fi
echo $branch_major $branch_minor
