Kijiji API
==========

Robot to post ads on Kijiji.

This Python program allows you to automatically post ads on
the [Kijiji] [1] advertisement community.
Using a crontab, you can program it to post your ad regularly and make sure
more users will see it.

[1]: http://www.kijiji.ca/  "Kijiji"

Usage
-----

First, store your Kijiji account username and password into the `config.ini` file.

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

Then, use the following command to post your add:
```
$ ./kijijiapi.py post -i img1.jpg,img2.png post-vars.txt
```
assuming that your images to join with the ad are `img1.jpg` and `img2.png`,
and your POST vars are in `post-vars.txt`.

Another way to include photos in your ad is to have them already posted on
Kijiji and include their link in the POST vars file:
```
Photo=http://mypic1.jpg,http://$_18.JPG
```

If you want to list the ads you currently have on Kijiji, use:
```
$ ./kijijiapi.py list
```
