import 'package:flutter/material.dart';

const Color primaryColor = Color(0xFF4A90E2);
const Color secondaryColor = Color(0xFF8E9AAF);
const Color favoriteColor = Color(0xFFEC4899);

Color getPrimaryColor(bool isDarkMode) {
  return isDarkMode ? Color(0xFF8E9AAF) : Color(0xFF4A90E2);
}

final Map<int, String> reverseRoundMapping = {
  1: '2018년 3월',
  2: '2017년 7월',
  3: '2017년 3월',
  4: '2016년 4월',
  5: '2015년 7월',
  6: '2015년 4월',
  7: '2014년 7월',
  8: '2014년 4월',
  9: '2012년 7월',
  10: '2012년 4월',
  11: '2011년 7월',
  12: '2011년 4월',
};


String examSessionToRoundName(dynamic examVal) {
  int? intVal = (examVal is int) ? examVal : int.tryParse(examVal.toString());
  return reverseRoundMapping[intVal] ?? '기타';
}


final List<String> categories = [
  '압연기능장'
];