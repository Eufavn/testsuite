{-# OPTIONS_GHC -fwarn-unsafe #-}
{-# OPTIONS_GHC -fenable-rewrite-rules #-}
-- | Basic test to see if no safe infer flag works
-- This module would usually infer safely, so it shouldn't be safe now.
module UnsafeInfered11_A where

f :: Int
f = 1

data T = T1 | T2 | T3 deriving ( Eq, Ord, Show )

lookupx :: Ord key => Show val => [(key,val)] -> key -> Maybe val
lookupx [] _                      = Nothing
lookupx ((t,a):xs) t' | t == t'   = Just a
                      | otherwise = lookupx xs t'

{-# RULES "lookupx/T" lookupx = tLookup #-}
tLookup :: [(T,a)] -> T -> Maybe a
tLookup [] _                      = Nothing
tLookup ((t,a):xs) t' | t /= t'   = Just a
                      | otherwise = tLookup xs t'

space = [(T1,"a"),(T2,"b"),(T3,"c")]
key = T3

main = do
    putStrLn $ "looking for " ++ show key
    putStrLn $ "in space " ++ show space
    putStrLn $ "Found: " ++ show (fromMaybe "Not Found!" $ lookupx space key)
    let b | Just "c" <- lookupx space key = "YES"
          | otherwise                     = "NO"
    putStrLn $ "Rules Disabled: " ++ b

fromMaybe :: a -> Maybe a -> a
fromMaybe a Nothing  = a
fromMaybe _ (Just a) = a

