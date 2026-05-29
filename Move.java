public class moveZero {
    public static int[] movezeros(int []arr) {
        int write=0;
        for(int read=0;read<arr.length;read++){
            if(arr[read]!=0){
                arr[write]=arr[read];
                write++;
            }
        }
        return arr;
    }
    public static void main(String[] args) {
      int []arr={0,1,0,3,12};
      int []newarr=arr[];
        System.out.println(newarr);
    }
}
