package com.example.badhibernate.examples;

/**
 * ALL GENERATED REFACTORING VARIANTS FOR TAXONOMY [T2]
 * Bottleneck: Nested loop linear search O(N^2) complexity
 * Original file (T2_InefficientAlgosExample.java) remains COMPLETELY UNTOUCHED.
 */
public class T2_InefficientAlgosExample_Variants {

    // ========================================================
    // VARIANT [v1] 🏆 [WINNER SELECTED BY KÙZODB / MAVEN]
    // ========================================================
    /*
public int findMatchesVariant1(List<String> listA, List<String> listB) {
    Set<String> setB = new HashSet<>(listB);
    int matches = 0;
    for (String itemA : listA) {
        if (setB.contains(itemA)) {
            matches++;
        }
    }
    return matches;
}
    */

    // ========================================================
    // VARIANT [v2] [CANDIDATE VARIANT]
    // ========================================================
    /*
public int findMatchesVariant2(List<String> listA, List<String> listB) {
    Set<String> setB = new HashSet<>(listB);
    return (int) listA.stream()
            .filter(setB::contains)
            .count();
}
    */

    // ========================================================
    // VARIANT [v3] [CANDIDATE VARIANT]
    // ========================================================
    /*
public int findMatchesVariant3(List<String> listA, List<String> listB) {
    // Create a sorted copy to avoid mutating the original list
    List<String> sortedB = new java.util.ArrayList<>(listB);
    java.util.Collections.sort(sortedB);
    
    int matches = 0;
    for (String itemA : listA) {
        if (java.util.Collections.binarySearch(sortedB, itemA) >= 0) {
            matches++;
        }
    }
    return matches;
}
    */

}
