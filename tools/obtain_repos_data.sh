echo "Vytvorit seznam vsech repozitaru"

repos=$(curl -H "Accept: application/vnd.github.v3+json" https://api.github.com/orgs/mlab-modules/repos?page=1 | jq '. | map(.ssh_url) | @sh'  | tr -d '"' | tr -d "\'")
repos=$repos$(curl -H "Accept: application/vnd.github.v3+json" https://api.github.com/orgs/mlab-modules/repos?page=2 | jq '. | map(.ssh_url) | @sh'  | tr -d '"' | tr -d "\'")
repos=$repos$(curl -H "Accept: application/vnd.github.v3+json" https://api.github.com/orgs/mlab-modules/repos?page=3 | jq '. | map(.ssh_url) | @sh'  | tr -d '"' | tr -d "\'")
repos=$repos$(curl -H "Accept: application/vnd.github.v3+json" https://api.github.com/orgs/mlab-modules/repos?page=4 | jq '. | map(.ssh_url) | @sh'  | tr -d '"' | tr -d "\'")
repos=$repos$(curl -H "Accept: application/vnd.github.v3+json" https://api.github.com/orgs/mlab-modules/repos?page=5 | jq '. | map(.ssh_url) | @sh'  | tr -d '"' | tr -d "\'")


#repos='git@github.com:mlab-modules/OLED01.git'

dir=$(pwd)/modules
dir_o=$(pwd)/out

echo " "
echo "Budu stahovat repozitare:"
echo $repos
echo " "

rm modules -r || true
#rm out -r || true
mkdir modules
#mkdir out
cd modules

#shopt -s extglob

for i in $repos; do
    f=$(basename $i .git);
    echo "Repo " $f;
    git clone $i --depth 1;

    if [ -d $f ]; then
      if [ -f $f/doc/metadata.yaml ]; then
        cd $dir/$f;

        echo "---" >> index.md;
        cat doc/metadata.yaml >> index.md;
        echo "---" >> index.md;
        cat README.md >> index.md;

        find . -type f -not \( -name '*jpg' -or -name '*svg' -or -name '*.pdf' -or -name '*.jpg' -or -name '*.md' -or -name '*.png' \) -delete

      else
        echo "Mazu.."
        sudo rm -r $f;
      fi
    fi

    cd $dir
done
