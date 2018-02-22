#!/bin/bash
#for file in `find /data/all_pack/qvm13m/xxxx/cab/6.0.0.2300/v3/360av -type f`
for file in `find /root/entSamples/tmp/virus_sample_20170922  -type f`
do
    #echo $file
	file_name=$(basename $file)
    #echo $file_name
    ndir=${file_name%%.*}
    #echo $ndir 

    7za x $file -o./mail_samples/$ndir
	#file_postfix=${file##*.}	

    #7za x $file -o./mail_samples/$file
	#file_dir=$(dirname $file)
	#file_name=$(basename $file)
	#file_postfix=${file##*.}	
	#if [ $file_postfix = "exe" ]
	#then
	#	echo $file_dir $file_name
		#cd $file_dir
		#cabextract $file_name
	#fi
done
exit 0
