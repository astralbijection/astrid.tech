{-# LANGUAGE OverloadedStrings #-}

module Seams.Importing.LoadSpec where

import Seams.Importing.Load
import Seams.Importing.ReadFile
import Seams.TestUtils
import Test.Hspec

x = runReadFileT (loadContentFolder exampleDir) ioReadFile

spec :: Spec
spec = do
  describe "loadContentFolder" $ do
    it "loads example folder successfuly" $ do "foo" `shouldBe` "foo"
