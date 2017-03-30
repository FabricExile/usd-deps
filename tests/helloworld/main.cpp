#include <stdio.h>

#include <pxr/usd/usd/stage.h>

int main(int argc, const char ** argv)
{
  UsdStage::CreateNew("c:\\temp\\test.usda");
  return 0;
}
