// SPDX-License-Identifier: MIT
import com.daedalus.world.RealmLandGrid;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.HashSet;

/** Standalone full-domain Java/native parity, plus an independent sorted-ring oracle. */
public class LandGridParity {
    static void require(boolean value) {if(!value) throw new AssertionError();}
    public static void main(String[] args) throws Exception {
        var lines=Files.readAllLines(Path.of(args[0])); require(lines.size()==10000);
        var seen=new HashSet<RealmLandGrid.Cell>(); int[] districts=new int[100];
        for(int i=0;i<10000;i++) {
            var c=RealmLandGrid.defaultCell(i);require(seen.add(c));districts[c.district()]++;
            String row=i+","+c.x()+","+c.z()+","+c.district()+","+c.offsetXcm()+","+c.offsetZcm();
            for(int n=1;n<=10;n++) row+=","+(c.fitsSquare(n)?1:0);
            require(row.equals(lines.get(i)));
        }
        // Rank each coordinate on an unbounded spiral, then sort the finite square.
        var oracle=new java.util.ArrayList<RealmLandGrid.Cell>();
        for(int z=-49;z<=50;z++) for(int x=-49;x<=50;x++) oracle.add(new RealmLandGrid.Cell(x,z));
        oracle.sort(java.util.Comparator.comparingInt(LandGridParity::rank));
        for(int i=0;i<10000;i++) require(oracle.get(i).equals(RealmLandGrid.defaultCell(i)));
        for(int count:districts) require(count==100);
        for(int bad:new int[]{-1,10000,Integer.MIN_VALUE,Integer.MAX_VALUE}) {
            try {RealmLandGrid.defaultCell(bad);throw new AssertionError();} catch(IllegalArgumentException expected) {}
        }
        require(!new RealmLandGrid.Cell(0,0).fitsSquare(Integer.MAX_VALUE));
        System.out.println("PASS: all 10000 coordinates, districts, offsets and 100000 footprint parity cases; independent ring oracle");
    }
    static int rank(RealmLandGrid.Cell c) {
        int x=c.x(),z=c.z(),r=Math.max(Math.abs(x),Math.abs(z));if(r==0)return 0;
        int base=(2*r-1)*(2*r-1);
        if(x==r && z>-r)return base+z+r-1;
        if(z==r)return base+2*r+r-x-1;
        if(x==-r)return base+4*r+r-z-1;
        return base+6*r+x+r-1;
    }
}
