import 'package:flutter/material.dart';
import 'package:google_mobile_ads/google_mobile_ads.dart';
import 'ad_helper.dart';

bool adsRemovedGlobal = false;

class MyBannerAd extends StatefulWidget {
  @override
  _MyBannerAdState createState() => _MyBannerAdState();
}

class _MyBannerAdState extends State<MyBannerAd> {
  BannerAd? _bannerAd;
  bool adsRemovedGlobal = false;


  @override
  void initState() {
    super.initState();
    if (!adsRemovedGlobal) { // 광고 제거가 구매되지 않은 상태일 때만 광고 생성
      _bannerAd = BannerAd(
        adUnitId: AdHelper.bannerAdUnitId,
        size: AdSize.banner,
        request: AdRequest(),
        listener: BannerAdListener(),
      )..load();
    }
  }

  @override
  void dispose() {
    _bannerAd?.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    if (adsRemovedGlobal || _bannerAd == null) {
      // 광고 제거 구매 상태이면 아무것도 반환하지 않음
      return SizedBox.shrink();
    }
    return Container(
      alignment: Alignment.center,
      width: _bannerAd!.size.width.toDouble(),
      height: _bannerAd!.size.height.toDouble(),
      child: AdWidget(ad: _bannerAd!),
    );
  }
}