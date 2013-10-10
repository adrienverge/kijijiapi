Kijiji-API
==========

Robot to post ads on Kijiji.

This set of bash functions allow you to automatically post ads on the
[Kijiji] [1] advertisement community.
Using a crontab, you can program it to post your ad regularly and make sure
more users will see it.

[1]: http://www.kijiji.ca/  Kijiji

Usage
-----

First, store your Kijiji account username and password into the `config` file.

To configure the script to post a specific ad, you need to post it once on
Kijiji and save the POST vars sent by your browser when posting:
```
POST /c-PostAd HTTP/1.1
```

Save this POST vars into a file (let's say `post-vars.txt`). Here is an example
showing how to format it:
```
CatId=650
RequestRefererUrl=%2C
ReformattedDesc=0
AdType=2
PriceAlternative=1
Price=20
Title=Great bike
Description=I'm selling my bike, it works great.<br><br>I also have a lock for it.
Photo=$global_ad_images
Email=my@email.com
Phone=555-555-5555
MapAddress=Montréal, QC, Canada
AddressCity=Montréal
AddressRegion=QC
AddressConfidenceLevel=0
AddressCounty=CA
AddressSelectedByUser=true
featuredAdDuration=0
```

Then, use the following functions to post your add:
```
$ source kijiji-api

$ sign_in
$ post_image bike.jpg
$ post_image lock.jpg
$ post_ad post-vars.txt
```
