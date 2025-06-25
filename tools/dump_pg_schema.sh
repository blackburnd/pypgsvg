pg_dump -h 192.168.1.xxx --format=plain -d am5_stag -U postgres -s -O -F plain --disable-triggers --encoding=UTF8 -f schema.dump
