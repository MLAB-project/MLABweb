#
# Tento skript slouzi k zaktualizovani a stazeni nove verze
# MLAB webu z docker hubu.
#
# Nasledne je vypne. NIXos (system) se nasledne postara o jejich 
# znovu spusteni. 
#
#

docker pull mlabproject/mlab-repository_updater;
docker pull mlabproject/mlabweb;

docker stop mlabweb_updater
docker stop mlabweb
